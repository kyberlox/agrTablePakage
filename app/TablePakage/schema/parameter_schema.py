# app/products/schema/parameter_schema.py
from pydantic import BaseModel
from typing import Optional, Dict, Any


class ParameterSchemaBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: str  # "Table" or "Formula"
    table_name: Optional[str] = None
    field_of_view: Optional[Dict[str, bool]] = None
    product_id: int


class ParameterSchemaCreate(ParameterSchemaBase):
    pass


class ParameterSchemaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    table_name: Optional[str] = None
    field_of_view: Optional[str] = None
    product_id: Optional[int] = None


class ParameterSchemaResponse(ParameterSchemaBase):
    id: int

    class Config:
        from_attributes = True
