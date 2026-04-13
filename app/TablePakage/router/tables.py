# app/products/router/tables.py
import os
import tempfile

from fastapi.responses import FileResponse
from fastapi import APIRouter, Depends, File, HTTPException
from fastapi import UploadFile

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import pandas as pd

from ..model.database import get_db
from ..utils.db_utils import create_table
from ..utils.router_utils import to_sql_name_kir, to_sql_name_lat

router = APIRouter(prefix="/tables", tags=["Tables"])


# === Table Schema Endpoints ===

@router.post("/upload_full_xlsx", description="Импорт всех параметров из XLSX.")
async def import_excel(
        product_id: int,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db)
):
    # Получаем product_name
    product_result = await db.execute(
        text("SELECT name FROM products WHERE id = :id"),
        {"id": product_id}
    )
    product_name = product_result.scalar_one_or_none()

    if product_name is None:
        raise HTTPException(status_code=404, detail="Продукция не найдена")

    table_name = f"{to_sql_name_lat(product_name)}_table"

    await create_table(db, table_name)

    # Читаем Excel
    df = pd.read_excel(file.file)
    df = df.where(pd.notnull(df), None)

    # Получаем колонки БД (без id)
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

    param_result = await db.execute(
        text("""
            SELECT name, transliterated_name
            FROM parameter_schemas
            WHERE product_id = :product_id
        """),
        {"product_id": product_id}
    )

    param_map = {
        row[0]: row[1]
        for row in param_result.fetchall()
    }

    excel_map = {}

    for col in df.columns:
        if col.lower() == "id":
            continue

        if col in param_map:
            excel_map[param_map[col]] = col
        else:
            translit = to_sql_name_lat(col)
            excel_map[translit] = col

    common_columns = set(excel_map.keys())

    if not common_columns:
        return {"message": "Нет колонок для вставки"}

    missing = common_columns - db_columns

    # Создаём недостающие
    for col in missing:
        await db.execute(
            text(f'ALTER TABLE "{table_name}" ADD COLUMN "{col}" TEXT')
        )
        await db.execute(
            text("""
                INSERT INTO parameter_schemas (
                    name,
                    transliterated_name,
                    type,
                    table_name,
                    product_id
                )
                VALUES (
                    :name,
                    :transliterated_name,
                    'Table',
                    :table_name,
                    :product_id
                )
                ON CONFLICT (transliterated_name, product_id)
                DO NOTHING
            """),
            {
                "name": excel_map[col],
                "transliterated_name": col,
                "table_name": table_name,
                "product_id": product_id
            }
        )

    await db.commit()

    # Формируем INSERT
    columns_sql = ", ".join(f'"{col}"' for col in common_columns)
    values_sql = ", ".join(f":{col}" for col in common_columns)

    insert_sql = text(f"""
        INSERT INTO {table_name} ({columns_sql})
        VALUES ({values_sql})
    """)

    # Вставляем строки
    for _, row in df.iterrows():
        values = {
            col: str(row[excel_map[col]]) if row[excel_map[col]] is not None else None
            for col in common_columns
        }
        await db.execute(insert_sql, values)

    dm_table = f"dm_product_{product_id}"

    # await mark_datamart_dirty(db, product_id)

    await db.commit()

    return {
        "table": table_name,
        "inserted_rows": len(df),
        "used_columns": list(common_columns)
    }


@router.post("/upload_matched_params_xlsx", description="Импорт параметров из XLSX, которые уже есть в базе данных.")
async def import_excel(
        product_id: int,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db)
):
    # Получаем product_name
    product_result = await db.execute(
        text("SELECT name FROM products WHERE id = :id"),
        {"id": product_id}
    )
    product_name = product_result.scalar_one_or_none()

    if product_name is None:
        raise HTTPException(status_code=404, detail="Продукция не найдена")

    table_name = f"{to_sql_name_lat(product_name)}_table"

    await create_table(db, table_name)

    # Читаем Excel
    df = pd.read_excel(file.file)
    df = df.where(pd.notnull(df), None)

    # Получаем колонки БД (без id)
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

    # Сопоставление: транслит → оригинальное имя из Excel
    excel_map = {
        to_sql_name_lat(col): col
        for col in df.columns
    }

    # Пересечение
    common_columns = db_columns & excel_map.keys()

    if not common_columns:
        return {"message": "Нет совпадающих колонок"}

    # Формируем INSERT
    columns_sql = ", ".join(f'"{col}"' for col in common_columns)
    values_sql = ", ".join(f":{col}" for col in common_columns)

    insert_sql = text(f"""
        INSERT INTO "{table_name}" ({columns_sql})
        VALUES ({values_sql})
    """)

    # Вставляем строки
    for _, row in df.iterrows():
        values = {
            col: str(row[excel_map[col]]) if row[excel_map[col]] is not None else None
            for col in common_columns
        }
        await db.execute(insert_sql, values)

    dm_table = f"dm_product_{product_id}"

    # await mark_datamart_dirty(db, product_id)

    await db.commit()

    return {
        "table": table_name,
        "inserted_rows": len(df),
        "used_columns": list(common_columns)
    }


@router.post("/download_xlsx", description="Выгрузка параметров из БД в XLSX.")
async def download_xlsx(
        product_id: int,
        db: AsyncSession = Depends(get_db)
):
    # Получаем product_name
    product_result = await db.execute(
        text("SELECT name FROM products WHERE id = :id"),
        {"id": product_id}
    )
    product_name = product_result.scalar_one_or_none()

    if product_name is None:
        raise HTTPException(status_code=404, detail="Продукция не найдена")

    table_name = f"{to_sql_name_lat(product_name)}_table"

    # Проверяем, что таблица существует
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

    # Получаем данные таблицы
    result = await db.execute(text(f"SELECT * FROM {table_name}"))
    rows = result.fetchall()
    columns = result.keys()

    if not rows:
        raise HTTPException(status_code=400, detail="Table is empty")

    # DataFrame
    df = pd.DataFrame(rows, columns=columns)

    # Переводим названия колонок и значения с латиницы на кириллицу, кроме названия колонок из SYSTEM_COLUMNS
    SYSTEM_COLUMNS = {"id"}

    df.columns = [
        to_sql_name_kir(col) if col not in SYSTEM_COLUMNS else col
        for col in df.columns
    ]
    df = df.applymap(
        lambda x: x if isinstance(x, str) else x
    )

    # Создаём временный XLSX
    tmp_dir = tempfile.gettempdir()
    file_path = os.path.join(tmp_dir, f"{table_name}_params.xlsx")

    df.to_excel(file_path, index=False, sheet_name="Parameters")

    # Отдаём файл
    return FileResponse(
        path=file_path,
        filename=f"{table_name}_params.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
