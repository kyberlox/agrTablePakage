# app/products/model/product.py
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import relationship
from .database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    manufacturer = Column(String(255))
    image = Column(String(512))  # Путь к файлу изображения
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связь с параметрами
    parameters = relationship("ParameterSchema", back_populates="product", cascade="all, delete-orphan")
