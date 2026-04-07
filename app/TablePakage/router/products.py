# app/products/router/products.py
import base64
import os
import re

from fastapi import APIRouter, Depends, File, HTTPException, Form, Body
from fastapi import UploadFile

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import uuid
from pathlib import Path
import imghdr

from ..model.database import get_db
from ..model.product import Product
from ..schema.product import ProductUpdate, ProductResponse

router = APIRouter(prefix="/products", tags=["Products"])

UPLOAD_DIR = "./static/images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Настройки
MAX_FILE_SIZE = 35 * 1024 * 1024  # 35 МБ
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


def generate_unique_filename(original_filename: str) -> str:
    ext = Path(original_filename).suffix
    unique_name = f"{uuid.uuid4()}{ext}"
    return unique_name


# функция декодирования изображения из base64
def save_base64_image(base64_string: str) -> str:
    match = re.match(r"data:image/(\w+);base64,(.+)", base64_string)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid base64 image format")

    ext = match.group(1)
    data = match.group(2)

    if f".{ext}" not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid image format")

    file_bytes = base64.b64decode(data)

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    return filename


# === Product Schema Endpoints ===

@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(
        name: str = Form(...),
        description: str = Form(None),
        manufacturer: str = Form(None),
        image: UploadFile = File(None),
        db: AsyncSession = Depends(get_db)
):
    
    image_path = None
    image_url = None

    if image:
        validate_image(image)
        unique_filename = generate_unique_filename(image.filename)
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        with open(file_path, "wb") as f:
            f.write(await image.read())
        image_path = file_path
        image_url = f"/api/files/images/{unique_filename}"

    db_product = Product(
        name=name,
        description=description,
        manufacturer=manufacturer,
        image=image_path,
        image_url=image_url
    )

    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)

    return db_product


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



@router.put("/{product_id}", response_model=ProductResponse, description="Запрос на изменение товара.")
async def edit_product(
    product_id: int, 
    name: str = Form(...),
    description: str = Form(None),
    manufacturer: str = Form(None),
    image: UploadFile = File(None),
    db: AsyncSession = Depends(get_db)):
    #!!!!!!!!!!! ПРОБЛЕМА С ЭТОЙ РУЧКОЙ "AttributeError: 'ProductUpdate' object has no attribute 'params'"
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    product.name = name
    product.description = description
    product.manufacturer = manufacturer

    #отдельно замена файла
    image_path = product.image

    if image:
        validate_image(image)
        if image_path is not None and image_path != "" and os.path.exists(image_path):
            with open(image_path, "wb") as f:
                f.write(await image.read())
        else:
            unique_filename = generate_unique_filename(image.filename)
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            with open(file_path, "wb") as f:
                f.write(await image.read())
            image_path = file_path
            image_url = f"/api/files/images/{unique_filename}"

            product.image = image_path
            product.image_url = image_url



    await db.commit()
    await db.refresh(product)
    return product

@router.delete("/{product_id}", response_model=ProductResponse, description="Запрос на удаление товара.")
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if product is None:
        return HTTPException(status_code=404, detail="Product not found")

    image_path = product.image
    if image_path is not None and image_path != "" and os.path.exists(image_path):
        os.remove(image_path)

    await db.delete(product)
    await db.commit()
    return product
