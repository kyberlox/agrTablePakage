from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import time

from app.TablePakage.model.database import get_db
from app.TablePakage.utils.router_utils import to_sql_name_lat
from app.TableSearch.schema.search import ModuleSearchResponse
from app.TableSearch.utils.dm_search import ensure_dm_exists, get_full_search_from_dm
from app.TableSearch.utils.formula_search import search_formula

router = APIRouter(prefix="/module_search", tags=["Module_search"])


# {
#     'id': int,
#     'name': str,
#     'description': str,
#     'all_values': list|str,
#     'responce_value': str,
#     'visibility': bool,
#     'required_type': str ('list'|'input')
# }

async def get_params_from_sql(db, table_name, schema_params, where_clauses, sql_params, allowed_params):
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

    return row, column_to_param

async def find_search_err(db, table_name, schema_params, where_clauses, sql_params, allowed_params, selected_params: dict[str, str | int] | None = dict()):
    #ищем неверно подобранный параметр
    where_clauses = []
    res = []
    for param_name, value in selected_params.items():
        if param_name not in allowed_params:
            continue

        if value is None:
            continue

        col = to_sql_name_lat(param_name)
        where_clauses.append(f'"{col}" = :{col}')
        sql_params[col] = str(value)

        req, column_to_param = await get_params_from_sql(db, table_name, schema_params, where_clauses, sql_params, allowed_params)

        # Проверяем на наличие ошибок в выбранных параметрах
        for param_name_next, value_next in selected_params.items():
            name_lat = to_sql_name_lat(param_name_next)
            if value_next not in req[name_lat]:
                #Ошибка, собираем json из тех что подходят и добавляем в значение ошибочного параметра ошибку
                err_param = {
                    "param_name" : param_name_next,
                    "error": f"Параметр {param_name_next} выбран не верно! \n Вы выбрали значение: {value_next}."
                }
                res.append(err_param)
            #если все ок, продолжаем итерацию пока не найдем ошибк
        break
    return res, req
    
            

@router.post(
    "/process_table_data",
    # response_model=ModuleSearchResponse,
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
    # schema_result = await db.execute(
    #     text("""
    #         SELECT name
    #         FROM parameter_schemas
    #         WHERE product_id = :product_id and type = 'Table'
    #     """),
    #     {"product_id": product_id},
    # )
    
    # schema_params = [row[0] for row in schema_result.fetchall()]
    
    schema_full_result = await db.execute(
        text("""
            SELECT *
            FROM parameter_schemas
            WHERE product_id = :product_id and type = 'Table'
        """),
        {"product_id": product_id},
    )

    full_info = schema_full_result.mappings().all()
    
    schema_params = [param_info['name'] for param_info in full_info]
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
        
        new_params = list()
        for item in full_info:
            name = item['name']
            value = parameters.get(name, None)
            responce_value = None
            if len(value) == 1:
                value = value[0]
                responce_value = value
            param_info = {
                'id': item.get('id', None),
                'name': name,
                'description': item.get('description', None),
                'all_values': value,
                'responce_value': responce_value,
                'visibility': item.get('visibility', None),
                'required_type': item.get('required_type', None)
            }
            new_params.append(param_info)
        

        # тут возвращаются формульные параметры
        # parameters = await search_formula(db, parameters, table_name)
        parameters = await search_formula(db, new_params, table_name)

        return {
            "product_id": product_id,
            "product_name": product_name,
            "parameters": parameters,
            # "parameters": new_params,
            "matched_rows": matched_rows,
            "request_time": time.perf_counter() - start_time,
        }

    # Формируем WHERE
    where_clauses = []
    sql_params = {}

    allowed_params = set(schema_params)
    formula_params = dict() # добавляю формульные параметры
    for param_name, value in selected_params.items():
        if param_name not in allowed_params:
            formula_params[param_name] = value
            continue

        if value is None:
            continue

        col = to_sql_name_lat(param_name)
        where_clauses.append(f'"{col}" = :{col}')
        sql_params[col] = str(value)

    #шлём собранный запрос
    row, column_to_param = await get_params_from_sql(db, table_name, schema_params, where_clauses, sql_params, allowed_params)
    full_value_parameters, matched_rows_1 = await get_full_search_from_dm(
            db,
            product_id,
        )
    if not row or row["matched_rows"] == 0:
        error_params, req = await find_search_err(db, table_name, schema_params, where_clauses, sql_params, allowed_params, selected_params)
        new_params = list()
        for item in full_info:
            name = item['name']
            name_lat = to_sql_name_lat(name)
            responce_value = None
            if name in selected_params:
                responce_value = selected_params[name]
            param_info = {
                'id': item.get('id', None),
                'name': name,
                'description': item.get('description', None),
                'all_values': full_value_parameters[name],
                'responce_value': responce_value,
                'visibility': item.get('visibility', None),
                'required_type': item.get('required_type', None),
                'filtered_values': req[name_lat]
            }
            is_param_error = [item for item in error_params if item['param_name'] == name]
            if is_param_error:
                param_info['responce_value'] = None
                param_info["error"] = is_param_error[0]["error"]
            new_params.append(param_info)

        parameters = await search_formula(db, new_params, table_name)
        return parameters

        # return {
        #     "product_id": product_id,
        #     "product_name": product_name,
        #     "parameters": [],
        #     "matched_rows": 0,
        #     'request_time': time.perf_counter() - start_time
        # }
    
    # Собираем значения параметров
    parameters = {
        param_name: sorted(str(v) for v in row[col])
        for col, param_name in column_to_param.items()
        if row[col]
    }
    parameters = dict()
    
    for col, param_name in column_to_param.items():
        if row[col] and len(row[col]) == 1:
            parameters[param_name] = row[col][0]
        elif row[col] and len(row[col]) > 1:
            parameters[param_name] = sorted(str(v) for v in row[col])

    #сюда функция формульного поиска
    """
    функция формульного поиска
    аргументы id продукта и словарь с параметрами
    """
    if formula_params:
        for key, value in formula_params.items():
            parameters[key] = value
    
    # await ensure_dm_exists(
    #         db,
    #         product_id,
    #         table_name,
    #         schema_params,
    #     )
    
    new_params = list()
    for item in full_info:
        name = item['name']
        value = parameters.get(name, None)
        responce_value = None
        if isinstance(value, str):
            responce_value = value
            value = full_value_parameters[name]
        param_info = {
            'id': item.get('id', None),
            'name': name,
            'description': item.get('description', None),
            'all_values': parameters.get(name, None),
            'responce_value': responce_value,
            'visibility': item.get('visibility', None),
            'required_type': item.get('required_type', None),
            'filtered_values': full_value_parameters[name]
        }
        new_params.append(param_info)

    parameters = await search_formula(db, new_params, table_name)
    
    
    return {
        "product_id": product_id,
        "product_name": product_name,
        "parameters": parameters,
        # "parameters": {},
        "matched_rows": row["matched_rows"],
        "request_time": time.perf_counter() - start_time,
    }

    # return {
    #     "product_id": product_id,
    #     "product_name": product_name,
    #     "table_parameters": table_parameters,
    #     "fromula_parameters": fromula_parameters,
    #     "matched_rows": row["matched_rows"],
    #     "request_time": time.perf_counter() - start_time,
    # }
