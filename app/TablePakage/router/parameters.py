# app/products/router/parameters.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..model.database import get_db
from ..model.product import Product
from ..model.parameter_schema import ParameterSchema
from ..schema.parameter_schema import ParameterSchemaCreate, ParameterSchemaResponse, ParameterSchemaUpdate
from ..utils.db_utils import create_or_alter_table
from ..utils.router_utils import to_sql_name_lat

router = APIRouter(prefix="/parameters", tags=["Parameters"])


# === Parameter Schema Endpoints ===

@router.post("/", response_model=ParameterSchemaResponse, status_code=201)
async def create_parameter_schema(
        schema: ParameterSchemaCreate,
        db: AsyncSession = Depends(get_db)
):
    # Проверка типа
    if schema.type not in ["Table", "Formula"]:
        raise HTTPException(status_code=400, detail="Type must be 'Table' or 'Formula'")

    # Проверка связи с продуктом
    product_result = await db.execute(
        select(Product).where(Product.id == schema.product_id)
    )
    if not product_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Invalid product_id")

    # Транслитерируем имя параметра
    translit_name = to_sql_name_lat(schema.name)

    db_schema = ParameterSchema(
        **schema.dict(),
        transliterated_name=to_sql_name_lat(schema.name)
    )

    db.add(db_schema)

    await db.flush()

    if db_schema.sort is None:
        db_schema.sort = float(db_schema.id)

    # Если тип Table — создаём или изменяем таблицу
    if schema.type == "Table":
        if not schema.table_name:
            raise HTTPException(status_code=400, detail="table_name is required")

        await create_or_alter_table(
            db,
            to_sql_name_lat(schema.table_name) + "_table",
            translit_name
        )

    await db.commit()
    await db.refresh(db_schema)
    return db_schema


@router.get("/by_product/{product_id}", response_model=list[ParameterSchemaResponse],
            description="Выведение информации по параметрам продукта по его {ID}.")
async def get_parameters(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ParameterSchema).where(ParameterSchema.product_id == product_id))
    params = result.scalars().all()
    if not params:
        raise HTTPException(status_code=404, detail="Parameters not found")
    return params


@router.get("/{param_id}", response_model=ParameterSchemaResponse,
            description="Выведение информации по параметру по его {ID}.")
async def get_parameter(param_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ParameterSchema).where(ParameterSchema.id == param_id))
    param = result.scalar_one_or_none()
    if not param:
        raise HTTPException(status_code=404, detail="Parameter not found")
    return param


@router.put("/{param_id}", response_model=ParameterSchemaResponse,
            description="Запрос на изменение полей параметра.")
async def update_parameter(
        param_id: int,
        schema_update: ParameterSchemaUpdate,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ParameterSchema).where(ParameterSchema.id == param_id))
    param = result.scalar_one_or_none()

    if not param:
        raise HTTPException(status_code=404, detail="Parameter not found")

    update_data = schema_update.dict(exclude_unset=True)

    if "name" in update_data:
        old_translit = param.transliterated_name
        new_translit = to_sql_name_lat(update_data["name"])

        param.name = update_data["name"]
        param.transliterated_name = new_translit

        # если это Table → переименовываем колонку
        if param.type == "Table" and param.table_name:
            table_name = to_sql_name_lat(param.table_name) + "_table"

            await db.execute(
                text(f'ALTER TABLE {table_name} RENAME COLUMN "{old_translit}" TO "{new_translit}"')
            )

    for key, value in update_data.items():
        if key != "name":
            setattr(param, key, value)

    await db.commit()
    await db.refresh(param)

    return param


@router.delete("/{param_id}", response_model=ParameterSchemaResponse,
               description="Запрос на удаление полей параметра.")
async def delete_parameter(
        param_id: int,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ParameterSchema).where(ParameterSchema.id == param_id)
    )
    param = result.scalar_one_or_none()

    if not param:
        raise HTTPException(status_code=404, detail="Parameter not found")

    await db.delete(param)
    await db.commit()

    return param
