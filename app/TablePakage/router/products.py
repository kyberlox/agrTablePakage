# app/products/router/products.py
import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form, Body
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import uuid
from pathlib import Path
import imghdr
import pandas as pd

from ..model.database import get_db
from ..model.product import Product
from ..model.parameter_schema import ParameterSchema
from ..schema.product import ProductCreate, ProductUpdate, ProductResponse
from ..schema.parameter_schema import ParameterSchemaCreate, ParameterSchemaResponse, ParameterSchemaUpdate
from ..utils.db_utils import create_or_alter_table

router = APIRouter(prefix="/products", tags=["Products"])

UPLOAD_DIR = "./static/images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Настройки
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 МБ
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}


def validate_image(file: UploadFile) -> None:
    # Проверка размера
    file.file.seek(0, 2)  # в конец
    size = file.file.tell()
    if size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max size is 5 MB.")
    file.file.seek(0)  # в начало

    # Проверка расширения
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file extension. Allowed: .jpg, .jpeg, .png, .gif")

    # Проверка содержимого
    content = file.file.read(1024)
    file.file.seek(0)
    img_type = imghdr.what(None, h=content)
    if not img_type:
        raise HTTPException(status_code=400, detail="Invalid image file")
    if ext == ".jpg" and img_type not in ["jpeg", "jpg"]:
        raise HTTPException(status_code=400, detail="File extension does not match content")


def generate_unique_filename(original_filename: str) -> str:
    ext = Path(original_filename).suffix
    unique_name = f"{uuid.uuid4()}{ext}"
    return unique_name


@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(
        name: str = Form(...),
        description: str = Form(None),
        manufacturer: str = Form(None),
        image: UploadFile = File(None),
        db: AsyncSession = Depends(get_db)
):
    image_path = None

    if image:
        validate_image(image)
        unique_filename = generate_unique_filename(image.filename)
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        with open(file_path, "wb") as f:
            f.write(await image.read())
        image_path = f"/static/images/{unique_filename}"

    db_product = Product(
        name=name,
        description=description,
        manufacturer=manufacturer,
        image=image_path
    )
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product


# === Product Schema Endpoints ===


@router.get("/", response_model=list[ProductResponse], description="Выведение всей продукции из БД.")
async def get_products(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/{product_id}", response_model=ProductResponse,
            description="Выведение вариации всех параметров товара по его {ID}.")
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# @router.post("/", response_model=ProductResponse, description="Запрос на добавление товара.")
# async def create_product(data: ProductCreate = Body(...),
#                          db: AsyncSession = Depends(get_db)
#                          ):
#     product = Product(
#         name=data.name,
#         description=data.description,
#         params=data.params
#     )
#     db.add(product)
#     await db.commit()
#     await db.refresh(product)
#     return product


@router.put("/{product_id}", response_model=ProductResponse, description="Запрос на изменение товара.")
async def edit_product(data: ProductUpdate = Body(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product).where(Product.id == data.id)
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    product.name = data.name
    product.description = data.description
    product.params = data.params
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", response_model=ProductResponse, description="Запрос на удаление товара.")
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if product is None:
        return HTTPException(status_code=404, detail="Product not found")

    await db.delete(product)
    await db.commit()
    return product


# === Parameter Schema Endpoints ===

@router.post("/parameters", response_model=ParameterSchemaResponse, status_code=201)
async def create_parameter_schema(
        schema: ParameterSchemaCreate,
        db: AsyncSession = Depends(get_db)
):
    # Проверка типа
    if schema.type not in ["Table", "Formula"]:
        raise HTTPException(status_code=400, detail="Type must be 'Table' or 'Formula'")

    # Проверка связи с продуктом
    product_result = await db.execute(select(Product).where(Product.id == schema.product_id))
    if not product_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Invalid product_id")

    db_schema = ParameterSchema(**schema.dict())
    db.add(db_schema)

    # Если тип Table — создаём или изменяем таблицу
    if schema.type == "Table":
        if not schema.table_name:
            raise HTTPException(status_code=400, detail="table_name is required for type 'Table'")
        await create_or_alter_table(db, schema.table_name, schema.name)

    await db.commit()
    await db.refresh(db_schema)
    return db_schema


@router.get("/parameters/{param_id}", response_model=ParameterSchemaResponse,
            description="Выведение информации по параметру по его {ID}.")
async def get_parameter(param_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ParameterSchema).where(ParameterSchema.id == param_id))
    param = result.scalar_one_or_none()
    if not param:
        raise HTTPException(status_code=404, detail="Parameter not found")
    return param


# @router.post("/parameters/xlsx", description="Запрос на добавление параметров из XLSX-файла.")
# def upload_parameters(uploaded_file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
#     if not uploaded_file.filename.endswith(".xlsx"):
#         raise HTTPException(status_code=400, detail="Требуется XLSX-файл")
#
#     df = pd.read_excel(uploaded_file.file)
#     descriptions = df.iloc[0]
#     dimensions = df.iloc[1]
#     values_rows = df.iloc[2:]
#
#     df = df.drop(df.columns[0], axis=1)
#
#     params_to_add = []
#
#     for col_name in df.columns:
#         name = col_name.strip()
#         description = str(descriptions[col_name])
#         dimension = str(dimensions[col_name])
#         raw_values = values_rows[col_name].dropna().tolist()
#         processed_values = []
#         for v in raw_values:
#             try:
#                 processed_values.append(float(v))
#             except (ValueError, TypeError):
#                 processed_values.append(str(v))
#
#         param = Params(
#             name=name,
#             description=description,
#             dimension=dimension,
#             values=processed_values
#         )
#         params_to_add.append(param)
#
#     db.add_all(params_to_add)
#     db.commit()
#
#     return {"Сообщение": "Записи из XLSX-файла добавлены в БД."}


@router.put("/parameters/{param_id}", response_model=ParameterSchemaResponse,
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

    for key, value in schema_update.dict(exclude_unset=True).items():
        setattr(param, key, value)

    await db.refresh(param)
    await db.commit()
    return param


@router.delete("/parameters/{param_id}", response_model=ParameterSchemaResponse,
               description="Запрос на удаление полей параметра.")
async def delete_parameter(
        param_id: int,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ParameterSchema).where(ParameterSchema.id == param_id))
    param = result.scalar_one_or_none()

    if result is None:
        return HTTPException(status_code=404, detail="Parameter not found")

    await db.delete(param)
    await db.commit()
    return param
