# app/products/model/datamart.py
from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .database import Base


class DataMartRegistry(Base):
    __tablename__ = "datamart_registry"

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        primary_key=True
    )

    dm_table_name = Column(String(255), nullable=False)

    is_dirty = Column(Boolean, nullable=False, default=True)

    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
        # ORM-связь
    product = relationship("Product", back_populates="datamart")
