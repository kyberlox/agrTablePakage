# app/products/model/parameter_schema.py
from sqlalchemy import Column, Integer, String, Text, DateTime, func, JSON, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class ParameterSchema(Base):
    __tablename__ = "parameter_schemas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(50), nullable=False)  # "Table" или "Formula"
    table_name = Column(String(255))  # Имя таблицы для типа "Table"
    field_of_view = Column(JSON, default=dict)  # Хранение JSON: {"admin": true, "user": false}

    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)  # Связь через внешний ключ

    # ORM-связь
    product = relationship("Product", back_populates="parameters")
