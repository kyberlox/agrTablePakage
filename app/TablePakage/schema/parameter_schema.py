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
    description: Optional[str] = None
    field_of_view: Optional[Dict[str, bool]] = None

class ParameterSchemaResponse(ParameterSchemaBase):
    id: int

    class Config:
        orm_mode = True
