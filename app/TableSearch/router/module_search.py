from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.TablePakage.model.database import get_db
from app.TablePakage.utils.router_utils import to_sql_name_lat
from app.TableSearch.schema.search import ModuleSearchResponse
import time


router = APIRouter(prefix="/module_search", tags=["Module_search"])


@router.post("/process_table_data",
             response_model=ModuleSearchResponse,
             description="Модуль подбора",
             )
async def process_table_data(
        product_id: int,
        selected_params: dict[str, str | int],
        db: AsyncSession = Depends(get_db)
):
    start_time = time.perf_counter()
    # Получаем product_id
    product_result = await db.execute(
        text("SELECT name FROM products WHERE id = :id"),
        {"id": product_id}
    )
    product_name = product_result.scalar_one_or_none()

    if product_name is None:
        raise HTTPException(status_code=404, detail="Продукция не найдена")

    table_name = f"{to_sql_name_lat(product_name)}_table"

    if not selected_params:
        raise HTTPException(status_code=400, detail="Параметры не переданы")

    # Параметры продукта (КИРИЛЛИЦА — ИСТИНА)
    schema_result = await db.execute(
        text("""
            SELECT name
            FROM parameter_schemas
            WHERE product_id = :product_id
        """),
        {"product_id": product_id}
    )
    schema_params = [row[0] for row in schema_result.fetchall()]
    if not schema_params:
        raise HTTPException(status_code=404, detail="Параметры не найдены")

    # WHERE по выбранным параметрам
    where_clauses = []
    sql_params = {}

    for param_name, value in selected_params.items():
        if value is None:
            continue

        col = to_sql_name_lat(param_name)
        where_clauses.append(f'"{col}" = :{col}')
        sql_params[col] = str(value)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    # Получаем строки
    query = f'SELECT * FROM "{table_name}" {where_sql}'
    result = await db.execute(text(query), sql_params)
    rows = result.fetchall()
    columns = result.keys()

    if not rows:
        return {
            "product_id": product_id,
            "product_name": product_name,
            "parameters": {},
            "matched_rows": 0
        }

    # Маппинг: sql_column → кириллическое имя
    column_to_param = {
        to_sql_name_lat(name): name
        for name in schema_params
    }

    # Собираем значения параметров
    parameters_result = {}

    for row in rows:
        row_dict = dict(zip(columns, row))

        for col, value in row_dict.items():
            if col == "id":
                continue
            if value in (None, "nan", "NaN"):
                continue

            param_name = column_to_param.get(col)
            if not param_name:
                continue

            parameters_result.setdefault(param_name, set()).add(str(value))

    # set → list
    parameters_result = {
        k: sorted(list(v))
        for k, v in parameters_result.items()
    }

    request_time = time.perf_counter() - start_time
    return {
        "product_id": product_id,
        "product_name": product_name,
        "parameters": parameters_result,
        "matched_rows": len(rows),
        "request_time": request_time
    }
