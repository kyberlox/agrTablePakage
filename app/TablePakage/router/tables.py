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

import io

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
    print("Файл называется: ", file.filename)
    print()
    # df = pd.read_excel(file.file)
    # contents = await file.read()
    # df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
    # df = df.where(pd.notnull(df), None)

    # Читаем Excel с обработкой ошибок
    contents = await file.read()

    try:
        # Пробуем прочитать с openpyxl (основной движок)
        df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
    except ValueError as e:
        if "Value must be one of" in str(e):
            # Если проблема со стилями — пробуем xlrd (для старых .xls)
            try:
                df = pd.read_excel(io.BytesIO(contents), engine='xlrd')
            except Exception as xlrd_error:
                raise HTTPException(
                    status_code=400,
                    detail=f"Файл содержит некорректные стили Excel. Не удалось прочитать ни openpyxl, ни xlrd: {xlrd_error}"
                )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Ошибка чтения Excel файла: {e}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Не удалось прочитать Excel файл: {e}"
        )

    df = df.where(pd.notnull(df), None)

    # Excel → SQL имена
    excel_map = {
        to_sql_name_lat(col): col
        for col in df.columns
        if col.lower() != "id"
    }
    excel_columns_ordered = [
        to_sql_name_lat(col)
        for col in df.columns
        if col.lower() != "id"
    ]

    excel_columns_set = set(excel_columns_ordered)

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
    columns_match = db_columns == excel_columns_set

    if not columns_match:
        # Удаляем таблицу
        await db.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))

        # Создаём заново с порядком столбцов как в excel-файле
        columns_sql = ", ".join(f'"{col}" TEXT' for col in excel_columns_ordered)

        await db.execute(text(f"""
            CREATE TABLE "{table_name}" (
                id SERIAL PRIMARY KEY,
                {columns_sql}
            )
        """))

        # Полностью пересобираем parameter_schemas
        await db.execute(
            text("""
                DELETE FROM parameter_schemas
                WHERE product_id = :product_id
            """),
            {"product_id": product_id}
        )

        # Добавляем заново в правильном порядке
        for col in excel_columns_ordered:
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
                """),
                {
                    "name": excel_map[col],
                    "transliterated_name": col,
                    "table_name": table_name,
                    "product_id": product_id
                }
            )
        await db.execute(text("""
            UPDATE parameter_schemas
            SET sort = id
            WHERE product_id = :product_id
              AND sort IS NULL
        """), {"product_id": product_id})

        # Удаляем колонки, которые не совпали
        # extra = db_columns - excel_columns_set
        #
        # for col in extra:
        #     # Удаляем из таблицы
        #     await db.execute(
        #         text(f'ALTER TABLE "{table_name}" DROP COLUMN "{col}"')
        #     )
        #
        #     # Удаляем из parameter_schemas
        #     await db.execute(
        #         text("""
        #             DELETE FROM parameter_schemas
        #             WHERE transliterated_name = :col
        #               AND product_id = :product_id
        #         """),
        #         {
        #             "col": col,
        #             "product_id": product_id
        #         }
        #     )

        # Перезаписываем данные в бд
        # await db.execute(text(f'DELETE FROM "{table_name}"'))

    await db.commit()

    # Делаем вставку в бд
    columns_sql = ", ".join(f'"{col}"' for col in excel_columns_ordered)
    values_sql = ", ".join(f":{col}" for col in excel_columns_ordered)

    insert_sql = text(f"""
        INSERT INTO "{table_name}" ({columns_sql})
        VALUES ({values_sql})
    """)

    rows = [
        {
            col: str(record[excel_map[col]]) if record[excel_map[col]] is not None else None
            for col in excel_columns_ordered
        }
        for record in df.to_dict(orient="records")
    ]

    await db.execute(insert_sql, rows)

    # Обновляем витрину datamart
    await mark_datamart_dirty(db, product_id)

    await db.commit()

    return {
        "table": table_name,
        "rows": len(df),
        "columns_match": columns_match,
        "columns": list(excel_columns_ordered)
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
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Access-Control-Expose-Headers": "Content-Disposition"}
    )
