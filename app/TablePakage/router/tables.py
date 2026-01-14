# app/products/router/tables.py
import os
import tempfile
from fastapi.responses import FileResponse
from fastapi import APIRouter, Depends, File, HTTPException
from fastapi import UploadFile

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import pandas as pd
from transliterate import translit

from ..model.database import get_db
from ..utils.router_utils import to_sql_name_kir, to_sql_name_lat

router = APIRouter(prefix="/tables", tags=["Tables"])


# === Table Schema Endpoints ===

@router.post("/upload_full_xlsx", description="Импорт всех параметров из XLSX.")
async def import_excel(
        product_name: str,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db)
):
    table_name = f"{to_sql_name_lat(product_name)}_table"

    product_result = await db.execute(
        text("SELECT id FROM products WHERE name = :name"),
        {"name": product_name}
    )
    product_id = product_result.scalar_one_or_none()

    if product_id is None:
        return {"message": f"Продукция '{product_name}' не найдена."}

    # 1. Читаем Excel
    df = pd.read_excel(file.file)
    df = df.where(pd.notnull(df), None)

    # 2. Получаем колонки БД (без id)
    result = await db.execute(
        text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = :table_name
              AND column_name != 'id'
        """),
        {"table_name": table_name}
    )

    db_columns = {row[0] for row in result.fetchall()}

    # 3. Сопоставление: транслит → оригинальное имя из Excel
    excel_map = {
        to_sql_name_lat(col): col
        for col in df.columns
        if col.lower() != "id"
    }

    common_columns =set(excel_map.keys())

    if not common_columns:
        return {"message": "Нет колонок для вставки"}

    missing = common_columns - db_columns

    # создаём недостающие
    for col in missing:
        await db.execute(
            text(f'ALTER TABLE {table_name} ADD COLUMN "{col}" TEXT')
        )
        await db.execute(
            text("""
                            INSERT INTO parameter_schemas (name, type, table_name, product_id)
                            SELECT
                            CAST(:name AS VARCHAR),
                            'Table',
                            CAST(:table_name AS VARCHAR),
                            :product_id
                            WHERE NOT EXISTS (
                                SELECT 1
                                FROM parameter_schemas
                                WHERE name = :name
                                  AND product_id = :product_id
                            )
                        """),
            {
                "name": col,
                "table_name": product_name,
                "product_id": product_id
            }
        )

    await db.commit()

    # 4. Формируем INSERT
    columns_sql = ", ".join(common_columns)
    values_sql = ", ".join(f":{col}" for col in common_columns)

    insert_sql = text(f"""
        INSERT INTO {table_name} ({columns_sql})
        VALUES ({values_sql})
    """)

    # 5. Вставляем строки
    for _, row in df.iterrows():
        values = {
            col: str(row[excel_map[col]]) if row[excel_map[col]] is not None else None
            for col in common_columns
        }
        await db.execute(insert_sql, values)

    await db.commit()

    return {
        "table": table_name,
        "inserted_rows": len(df),
        "used_columns": list(common_columns)
    }

@router.post("/upload_matched_params_xlsx", description="Импорт параметров из XLSX, которые уже есть в базе данных.")
async def import_excel(
        product_name: str,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db)
):
    table_name = f"{to_sql_name_lat(product_name)}_table"

    # 1. Читаем Excel
    df = pd.read_excel(file.file)
    df = df.where(pd.notnull(df), None)

    # 2. Получаем колонки БД (без id)
    result = await db.execute(
        text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = :table_name
              AND column_name != 'id'
        """),
        {"table_name": table_name}
    )
    db_columns = {row[0] for row in result.fetchall()}

    # 3. Сопоставление: транслит → оригинальное имя из Excel
    excel_map = {
        to_sql_name_lat(col): col
        for col in df.columns
    }

    # 4. Пересечение
    common_columns = db_columns & excel_map.keys()

    if not common_columns:
        return {"message": "Нет совпадающих колонок"}

    # 5. Формируем INSERT
    columns_sql = ", ".join(common_columns)
    values_sql = ", ".join(f":{col}" for col in common_columns)

    insert_sql = text(f"""
        INSERT INTO {table_name} ({columns_sql})
        VALUES ({values_sql})
    """)

    # 6. Вставляем строки
    for _, row in df.iterrows():
        values = {
            col: str(row[excel_map[col]]) if row[excel_map[col]] is not None else None
            for col in common_columns
        }
        await db.execute(insert_sql, values)

    await db.commit()

    return {
        "table": table_name,
        "inserted_rows": len(df),
        "used_columns": list(common_columns)
    }


@router.post("/download_xlsx", description="Выгрузка параметров из БД в XLSX.")
async def download_xlsx(
        product_name: str,
        db: AsyncSession = Depends(get_db)
):
    table_name = f"{to_sql_name_lat(product_name)}_table"

    # 1. Проверяем, что таблица существует
    exists = await db.execute(
        text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_name = :table_name
            )
        """),
        {"table_name": table_name}
    )

    if not exists.scalar():
        raise HTTPException(status_code=404, detail="Table not found")

    # 2. Получаем данные таблицы
    result = await db.execute(text(f"SELECT * FROM {table_name}"))
    rows = result.fetchall()
    columns = result.keys()

    if not rows:
        raise HTTPException(status_code=400, detail="Table is empty")

    # 3. DataFrame
    df = pd.DataFrame(rows, columns=columns)

    # 4. Переводим названия колонок и значения с латиницы на кириллицу, кроме названия колонок из SYSTEM_COLUMNS
    SYSTEM_COLUMNS = {"id"}

    df.columns = [
        to_sql_name_kir(col) if col not in SYSTEM_COLUMNS else col
        for col in df.columns
    ]
    df = df.applymap(
        lambda x: x if isinstance(x, str) else x
    )

    # 5. Создаём временный XLSX
    tmp_dir = tempfile.gettempdir()
    file_path = os.path.join(tmp_dir, f"{table_name}_params.xlsx")

    df.to_excel(file_path, index=False, sheet_name="Parameters")

    # 6. Отдаём файл
    return FileResponse(
        path=file_path,
        filename=f"{table_name}_params.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
