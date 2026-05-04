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
from .parameter_values import mark_datamart_dirty

router = APIRouter(prefix="/tables", tags=["Tables"])


# === Table Schema Endpoints ===


@router.post("/upload_xlsx", description="Импорт параметров из XLSX с авто-синхронизацией")
async def upload_xlsx(
        product_id: int,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db)
):
    # Получаем продукт
    product_result = await db.execute(
        text("SELECT name FROM products WHERE id = :id"),
        {"id": product_id}
    )
    product_name = product_result.scalar_one_or_none()

    if product_name is None:
        raise HTTPException(status_code=404, detail="Продукция не найдена")

    table_name = f"{to_sql_name_lat(product_name)}_table"

    # Создаём таблицу если нет
    await create_table(db, table_name)

    # Читаем Excel
    print("Файл называется: ", file.file)
    print()
    df = pd.read_excel(file.file, engine='openpyxl')
    df = df.where(pd.notnull(df), None)

    # Excel → SQL имена
    excel_map = {
        to_sql_name_lat(col): col
        for col in df.columns
        if col.lower() != "id"
    }
    excel_columns = set(excel_map.keys())

    # Получаем колонки БД
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

    # Проверка совпадения
    columns_match = db_columns == excel_columns

    if not columns_match:
        # Добавляем новые колонки
        missing = excel_columns - db_columns

        for col in missing:
            # Колонка в таблицу
            await db.execute(
                text(f'ALTER TABLE "{table_name}" ADD COLUMN "{col}" TEXT')
            )

            # Добавляем в parameter_schemas
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
                    "name": excel_map[col],  # оригинальное имя из Excel
                    "transliterated_name": col,
                    "table_name": table_name,
                    "product_id": product_id
                }
            )

        # Удаляем колонки, которые не совпали
        extra = db_columns - excel_columns

        for col in extra:
            # Удаляем из таблицы
            await db.execute(
                text(f'ALTER TABLE "{table_name}" DROP COLUMN "{col}"')
            )

            # Удаляем из parameter_schemas
            await db.execute(
                text("""
                    DELETE FROM parameter_schemas
                    WHERE transliterated_name = :col
                      AND product_id = :product_id
                """),
                {
                    "col": col,
                    "product_id": product_id
                }
            )

        await db.commit()

        # Перезаписываем данные в бд
        await db.execute(text(f'DELETE FROM "{table_name}"'))

    # Делаем вставку в бд
    columns_sql = ", ".join(f'"{col}"' for col in excel_columns)
    values_sql = ", ".join(f":{col}" for col in excel_columns)

    insert_sql = text(f"""
        INSERT INTO "{table_name}" ({columns_sql})
        VALUES ({values_sql})
    """)

    rows = [
        {
            col: str(row[excel_map[col]]) if row[excel_map[col]] is not None else None
            for col in excel_columns
        }
        for _, row in df.iterrows()
    ]

    await db.execute(insert_sql, rows)

    # Обновляем витрину datamart
    await mark_datamart_dirty(db, product_id)

    await db.commit()

    return {
        "table": table_name,
        "rows": len(df),
        "columns_match": columns_match,
        "columns": list(excel_columns)
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
