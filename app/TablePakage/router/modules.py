from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ..model.database import get_db
from ..utils.router_utils import to_sql_name_lat

router = APIRouter(prefix="/modules", tags=["Modules"])


@router.post("/process_table_data",
             description="Модуль подбора",
             response_model=dict)
async def process_table_data(
        product_id: int,
        param_id: int,
        db: AsyncSession = Depends(get_db)
):
    # Получаем product_id
    product_result = await db.execute(
        text("SELECT name FROM products WHERE id = :id"),
        {"id": product_id}
    )
    product_name = product_result.scalar_one_or_none()

    if product_name is None:
        raise HTTPException(status_code=404, detail="Продукция не найдена")

    table_name = f"{to_sql_name_lat(product_name)}_table"

    # Получаем param_id
    param_result = await db.execute(
        text("""
            SELECT name
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

    # Проверяем, что таблица сущ-ет
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

    # Проверяем, что колонка параметра существует в таблице
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
            "column_name": to_sql_name_lat(param_name)
        }
    )

    if not column_exists.scalar():
        raise HTTPException(status_code=404, detail=f"Колонка параметра не найдена в таблице")

    # Получаем данные из таблицы
    result = await db.execute(text(f"SELECT * FROM {table_name}"))
    rows = result.fetchall()
    columns = result.keys()

    if not rows:
        return {
            "product_id": product_id,
            "product_name": product_name,
            "param_id": param_id,
            "param_name": param_name,
            "message": "Таблица пуста",
            "processed_data": [],
            "statistics": {}
        }

    processed_data = []
    param_values = []
    param_column_name = to_sql_name_lat(param_name)

    for row in rows:
        row_dict = {}
        for i, column in enumerate(columns):
            row_dict[column] = row[i]

        if param_column_name in row_dict:
            param_value = row_dict[param_column_name]
            if param_value is not None:
                param_values.append(param_value)

        row_dict['has_param_value'] = row_dict.get(param_column_name) is not None

        processed_data.append(row_dict)