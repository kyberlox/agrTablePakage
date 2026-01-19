# app/products/router/tables.py
import os
import tempfile
from typing import Optional

from fastapi.responses import FileResponse
from fastapi import APIRouter, Depends, File, HTTPException
from fastapi import UploadFile

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import pandas as pd

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
        if col.lower() != "id"
    }

    common_columns = set(excel_map.keys())

    if not common_columns:
        return {"message": "Нет колонок для вставки"}

    missing = common_columns - db_columns

    # Создаём недостающие
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

    # Формируем INSERT
    columns_sql = ", ".join(common_columns)
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
    columns_sql = ", ".join(common_columns)
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


@router.get("/get_unique_param", description="Получение уникальных значений выбранного параметра из БД.")
async def get_unique_param(
        product_name: str,
        param_name: str,
        db: AsyncSession = Depends(get_db)
):
    table_name = f"{to_sql_name_lat(product_name)}_table"
    param_name = to_sql_name_lat(param_name)

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

    # Проверяем, что колонка существует
    column_exists = await db.execute(
        text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = :table_name
                  AND column_name = :column_name
            )
        """),
        {
            "table_name": table_name,
            "column_name": param_name
        }
    )

    if not column_exists.scalar():
        raise HTTPException(status_code=404, detail="Column not found")

    # Получаем данные таблицы
    result = await db.execute(text(f"SELECT {param_name} FROM {table_name}"))
    values = set([row[0] for row in result.fetchall()])

    if not values:
        raise HTTPException(status_code=400, detail="Table is empty")

    return {
        "parameter": param_name,
        "values": values
    }


@router.post("/delete_selected_value_of_param", description="Удаление выбранного значения из параметра в БД.")
async def get_unique_param(
        product_name: str,
        param_name: str,
        value: Optional[str] = None,
        db: AsyncSession = Depends(get_db)
):
    table_name = f"{to_sql_name_lat(product_name)}_table"
    param_name = to_sql_name_lat(param_name)

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

    # Проверяем, что колонка существует
    column_exists = await db.execute(
        text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = :table_name
                  AND column_name = :column_name
            )
        """),
        {
            "table_name": table_name,
            "column_name": param_name
        }
    )

    if not column_exists.scalar():
        raise HTTPException(status_code=404, detail="Column not found")

    # Удаляем данные таблицы
    if value is None:
        delete_sql = text(f"""
                DELETE FROM "{table_name}"
                WHERE "{param_name}" IS NULL
            """)
        params = {}
    else:
        delete_sql = text(f"""
                DELETE FROM "{table_name}"
                WHERE "{param_name}" = :value
            """)
        params = {"value": value}

    await db.execute(delete_sql, params)
    await db.commit()

    return {
        "table": table_name,
        "parameter": param_name,
        "deleted_value": value,
    }


@router.post("/added_value_for_param", description="Добавление значения для выбранного параметра в БД.")
async def get_unique_param(
        product_name: str,
        param_name: str,
        value: Optional[str] = None,
        db: AsyncSession = Depends(get_db)
):
    table_name = f"{to_sql_name_lat(product_name)}_table"
    param_name = to_sql_name_lat(param_name)

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

    # Проверяем, что колонка существует
    column_exists = await db.execute(
        text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = :table_name
                  AND column_name = :column_name
            )
        """),
        {
            "table_name": table_name,
            "column_name": param_name
        }
    )

    if not column_exists.scalar():
        raise HTTPException(status_code=404, detail="Column not found")

    # Получаем данные таблицы
    result = await db.execute(
        text(f"""
            SELECT "{param_name}"
            FROM "{table_name}"
            WHERE "{param_name}" IS NOT NULL
        """)
    )
    values = [row[0] for row in result.fetchall()]

    if not values:
        # все значения в выбранной колонке - NULL
        await db.execute(
            text(f"""
                UPDATE "{table_name}"
                SET "{param_name}" = :new_value
            """),
            {"new_value": value}
        )
        await db.commit()

        return {
            "parameter": param_name,
            "new_value": value,
            "mode": "updated_null_column"
        }

    else:
        # считаем количество записей для каждого значения
        count_result = await db.execute(
            text(f"""
                    SELECT "{param_name}", COUNT(*) AS cnt
                    FROM "{table_name}"
                    WHERE "{param_name}" IS NOT NULL
                    GROUP BY "{param_name}"
                """)
        )

        rows = count_result.fetchall()
        if not rows:
            raise HTTPException(status_code=400, detail="No values to duplicate")

        # значение с максимальным количеством записей
        max_value = max(rows, key=lambda r: r[1])[0]

        # получаем все колонки таблицы, кроме id
        cols_result = await db.execute(
            text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = :table_name
                      AND column_name != 'id'
                """),
            {"table_name": table_name}
        )

        columns = [r[0] for r in cols_result.fetchall()]

        # формируем SELECT: заменяем только param_name
        select_columns = []
        for col in columns:
            if col == param_name:
                select_columns.append(":new_value AS " + col)
            else:
                select_columns.append(f'"{col}"')

        insert_sql = text(f"""
                INSERT INTO "{table_name}" ({", ".join(f'"{c}"' for c in columns)})
                SELECT {", ".join(select_columns)}
                FROM "{table_name}"
                WHERE "{param_name}" = :max_value
            """)

        await db.execute(
            insert_sql,
            {
                "new_value": value,
                "max_value": max_value
            }
        )

        await db.commit()

        return {
            "parameter": param_name,
            "new_value": value,
            "copied_from": max_value,
            "mode": "duplicated_rows"
        }
