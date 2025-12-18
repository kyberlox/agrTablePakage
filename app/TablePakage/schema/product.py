# app/products/schema/product.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    manufacturer: Optional[str] = None
    image_url: Optional[str] = None  # ← новое поле

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    image: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
