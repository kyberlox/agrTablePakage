# app/products/utils/db_utils.py
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import re

# Проверка корректности имени таблицы/колонки
def is_valid_identifier(name: str) -> bool:
    return re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name) is not None

async def create_or_alter_table(
    db: AsyncSession,
    table_name: str,
    column_name: str
):
    if not is_valid_identifier(table_name) or not is_valid_identifier(column_name):
        raise ValueError("Invalid table or column name")

    # Проверяем, существует ли таблица
    result = await db.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = :table_name
        );
    """), {"table_name": table_name})

    table_exists = result.scalar()

    if not table_exists:
        # Создаём таблицу с колонкой
        await db.execute(text(f"""
            CREATE TABLE {table_name} (
                id SERIAL PRIMARY KEY,
                {column_name} TEXT
            );
        """))
        await db.commit()
    else:
        # Проверяем, есть ли колонка
        result = await db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = :table_name AND column_name = :column_name
            );
        """), {"table_name": table_name, "column_name": column_name})

        column_exists = result.scalar()
        if not column_exists:
            # Добавляем колонку
            await db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT;"))
            await db.commit()
