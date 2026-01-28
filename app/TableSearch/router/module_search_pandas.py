from sqlalchemy import text
import pandas as pd
from fastapi import Depends, HTTPException, APIRouter
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from app.TablePakage.model.database import get_db
from app.TablePakage.utils.router_utils import to_sql_name_lat
from app.TableSearch.model.database_pandas import sync_engine
from app.TableSearch.schema.search import ModuleSearchResponse
import time


def process_with_pandas(
        table_name: str,
        selected_params: dict[str, str | int],
):
    df = pd.read_sql_table(table_name, con=sync_engine)

    for param_name, value in selected_params.items():
        if value is None:
            continue

        col = to_sql_name_lat(param_name)
        if col not in df.columns:
            continue

        df = df[df[col] == str(value)]

    if df.empty:
        return {}, 0

    parameters: dict[str, list[str]] = {}

    for col in df.columns:
        if col == "id":
            continue

        values = (
            df[col]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        if values:
            parameters[col.replace("_", " ").title()] = sorted(values)

    return parameters, len(df)


router = APIRouter(prefix="/module_search", tags=["Module_search"])


@router.post(
    "/process_table_data_pandas",
    response_model=ModuleSearchResponse,
    description="Модуль подбора",
)
async def process_table_data(
        product_id: int,
        selected_params: dict[str, str | int],
        db: AsyncSession = Depends(get_db)
):
    start_time = time.perf_counter()
    # 1. Получаем продукт
    product_result = await db.execute(
        text("SELECT name FROM products WHERE id = :id"),
        {"id": product_id}
    )
    product_name = product_result.scalar_one_or_none()

    if product_name is None:
        raise HTTPException(status_code=404, detail="Продукция не найдена")

    if not selected_params:
        raise HTTPException(status_code=400, detail="Параметры не переданы")

    table_name = f"{to_sql_name_lat(product_name)}_table"

    # 2. НЕБЛОКИРУЮЩИЙ вызов pandas
    parameters, matched_rows = await run_in_threadpool(
        process_with_pandas,
        table_name,
        selected_params,
    )

    request_time = time.perf_counter() - start_time
    return {
        "product_id": product_id,
        "product_name": product_name,
        "parameters": parameters,
        "matched_rows": matched_rows,
        "request_time": request_time
    }
