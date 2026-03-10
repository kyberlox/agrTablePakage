from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import time

from app.TablePakage.model.database import get_db
from app.TablePakage.utils.router_utils import to_sql_name_lat
from app.TableSearch.schema.search import ModuleSearchResponse
from app.TableSearch.utils.dm_search import ensure_dm_exists, get_full_search_from_dm

router = APIRouter(prefix="/module_search", tags=["Module_search"])


@router.post(
    "/process_table_data",
    response_model=ModuleSearchResponse,
    description="Модуль подбора",
)
async def process_table_data(
        product_id: int,
        selected_params: dict[str, str | int] | None = Body(None),
        db: AsyncSession = Depends(get_db),
):
    start_time = time.perf_counter()
    selected_params = selected_params or {}

    # Получаем продукцию
    product_result = await db.execute(
        text("SELECT name FROM products WHERE id = :id"),
        {"id": product_id},
    )
    product_name = product_result.scalar_one_or_none()

    if not product_name:
        raise HTTPException(status_code=404, detail="Продукция не найдена")

    table_name = f"{to_sql_name_lat(product_name)}_table"

    # Получаем параметры продукции
    schema_result = await db.execute(
        text("""
            SELECT name
            FROM parameter_schemas
            WHERE product_id = :product_id
        """),
        {"product_id": product_id},
    )
    schema_params = [row[0] for row in schema_result.fetchall()]

    if not schema_params:
        raise HTTPException(status_code=404, detail="Параметры не найдены")

    if not selected_params:
        await ensure_dm_exists(
            db,
            product_id,
            table_name,
            schema_params,
        )

        parameters, matched_rows = await get_full_search_from_dm(
            db,
            product_id,
        )

        return {
            "product_id": product_id,
            "product_name": product_name,
            "parameters": parameters,
            "matched_rows": matched_rows,
            "request_time": time.perf_counter() - start_time,
        }

    # Формируем WHERE
    where_clauses = []
    sql_params = {}

    allowed_params = set(schema_params)

    for param_name, value in selected_params.items():
        if param_name not in allowed_params:
            continue

        if value is None:
            continue

        col = to_sql_name_lat(param_name)
        where_clauses.append(f'"{col}" = :{col}')
        sql_params[col] = str(value)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    # Запрашиваем строки
    select_parts = []
    column_to_param = {}

    for param_name in schema_params:
        col = to_sql_name_lat(param_name)
        select_parts.append(
            f'array_agg(DISTINCT "{col}") FILTER (WHERE "{col}" IS NOT NULL) AS "{col}"'
        )
        column_to_param[col] = param_name

    select_sql = ", ".join(select_parts)

    query = f"""
            SELECT
                {select_sql},
                COUNT(*) AS matched_rows
            FROM "{table_name}"
            {where_sql}
        """

    result = await db.execute(text(query), sql_params)
    row = result.mappings().first()

    if not row or row["matched_rows"] == 0:
        return {
            "product_id": product_id,
            "product_name": product_name,
            "parameters": {},
            "matched_rows": 0,
        }

    # Собираем значения параметров
    parameters = {
        param_name: sorted(str(v) for v in row[col])
        for col, param_name in column_to_param.items()
        if row[col]
    }

    return {
        "product_id": product_id,
        "product_name": product_name,
        "parameters": parameters,
        "matched_rows": row["matched_rows"],
        "request_time": time.perf_counter() - start_time,
    }
