# app/products/router/parameter_values.py
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..model.database import get_db
from ..utils.router_utils import to_sql_name_lat

router = APIRouter(prefix="/parameter_values", tags=["Parameter_values"])


# Функция для обновления витрины при внесении изменений
async def mark_datamart_dirty(db, product_id):
    await db.execute(
        text("""
            INSERT INTO datamart_registry (
                product_id,
                dm_table_name,
                is_dirty,
                updated_at
            )
            VALUES (
                :product_id,
                :dm_table_name,
                TRUE,
                now()
            )
            ON CONFLICT (product_id)
            DO UPDATE
            SET is_dirty = TRUE,
                updated_at = now()
        """),
        {
            "product_id": product_id,
            "dm_table_name": f"dm_product_{product_id}"
        }
    )


@router.get("/get_unique_param", description="Получение уникальных значений выбранного параметра из БД.")
async def get_unique_param(
        product_id: int,
        param_id: int,
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

    # Получаем param_name
    param_result = await db.execute(
        text("""
                SELECT transliterated_name
                FROM parameter_schemas
                WHERE id = :param_id
                  AND product_id = :product_id
            """),
        {
            "param_id": param_id,
            "product_id": product_id
        }
    )
    param_name = param_result.scalar_one_or_none()

    if param_name is None:
        raise HTTPException(status_code=404, detail="Параметр не найден")

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
    result = await db.execute(text(f'SELECT "{param_name}" FROM "{table_name}"'))
    values = set([row[0] for row in result.fetchall()])

    if not values:
        raise HTTPException(status_code=400, detail="Table is empty")

    return {
        "parameter": param_name,
        "values": values
    }


@router.post("/edit_value_for_param", description="Изменение значения для выбранного параметра в БД.")
async def edit_value_of_param(
        product_id: int,
        param_id: int,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        db: AsyncSession = Depends(get_db)
):
    # Получаем product_named
    product_result = await db.execute(
        text("SELECT name FROM products WHERE id = :id"),
        {"id": product_id}
    )
    product_name = product_result.scalar_one_or_none()

    if product_name is None:
        raise HTTPException(status_code=404, detail="Продукция не найдена")

    table_name = f"{to_sql_name_lat(product_name)}_table"

    # Получаем param_name
    param_result = await db.execute(
        text("""
                   SELECT transliterated_name
                   FROM parameter_schemas
                   WHERE id = :param_id
                     AND product_id = :product_id
               """),
        {
            "param_id": param_id,
            "product_id": product_id
        }
    )
    param_name = param_result.scalar_one_or_none()

    if param_name is None:
        raise HTTPException(status_code=404, detail="Параметр не найден")

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

    if old_value is None:
        where_sql = f'"{param_name}" IS NULL'
        params = {"new_value": new_value}
    else:
        where_sql = f'"{param_name}" = :old_value'
        params = {"new_value": new_value, "old_value": old_value}

    result = await db.execute(
        text(f"""
            UPDATE "{table_name}"
            SET "{param_name}" = :new_value
            WHERE {where_sql}
        """),
        params
    )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Значение не найдено")

    await mark_datamart_dirty(db, product_id)

    await db.commit()

    return {
        "parameter": param_name,
        "new_value": new_value,
    }


@router.post("/delete_selected_value_of_param", description="Удаление выбранного значения из параметра в БД.")
async def delete_selected_value_of_param(
        product_id: int,
        param_id: int,
        value: Optional[str] = None,
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

    # Получаем param_name
    param_result = await db.execute(
        text("""
                   SELECT transliterated_name
                   FROM parameter_schemas
                   WHERE id = :param_id
                     AND product_id = :product_id
               """),
        {
            "param_id": param_id,
            "product_id": product_id
        }
    )
    param_name = param_result.scalar_one_or_none()

    if param_name is None:
        raise HTTPException(status_code=404, detail="Параметр не найден")

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

    dm_table = f"dm_product_{product_id}"

    await mark_datamart_dirty(db, product_id)

    await db.commit()

    return {
        "table": table_name,
        "parameter": param_name,
        "deleted_value": value,
    }


@router.post("/added_value_for_param", description="Добавление значения для выбранного параметра в БД.")
async def added_value_for_param(
        product_id: int,
        param_id: int,
        value: Optional[str] = None,
        db: AsyncSession = Depends(get_db)
):
    # Получаем product_named
    product_result = await db.execute(
        text("SELECT name FROM products WHERE id = :id"),
        {"id": product_id}
    )
    product_name = product_result.scalar_one_or_none()

    if product_name is None:
        raise HTTPException(status_code=404, detail="Продукция не найдена")

    table_name = f"{to_sql_name_lat(product_name)}_table"

    # Получаем param_name
    param_result = await db.execute(
        text("""
                   SELECT transliterated_name
                   FROM parameter_schemas
                   WHERE id = :param_id
                     AND product_id = :product_id
               """),
        {
            "param_id": param_id,
            "product_id": product_id
        }
    )
    param_name = param_result.scalar_one_or_none()

    if param_name is None:
        raise HTTPException(status_code=404, detail="Параметр не найден")

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
        dm_table = f"dm_product_{product_id}"

        await mark_datamart_dirty(db, product_id)

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

        dm_table = f"dm_product_{product_id}"

        await mark_datamart_dirty(db, product_id)

        await db.commit()

        return {
            "parameter": param_name,
            "new_value": value,
            "copied_from": max_value,
            "mode": "duplicated_rows"
        }
