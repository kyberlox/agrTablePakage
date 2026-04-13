# app/products/schema/parameter_schema.py
from pydantic import BaseModel
from typing import Optional, Dict, Any


class ConstantsSchemaBase(BaseModel):
    name: str
    description: Optional[str] = None
    value: float
    result_param_id: int


class ConstantsSchemaCreate(ConstantsSchemaBase):
    pass

class ConstantsSchemaGet(ConstantsSchemaBase):
    id: int
    name: Optional[str] = None
    description: Optional[str] = None
    value: Optional[float] = None
    # parametr_schema_id: Optional[int] = None
    parameter_schema_name: Optional[str] = None


class ConstantsSchemaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    value: Optional[float] = None
    result_param_id: Optional[int] = None


class ConstantsSchemaResponse(ConstantsSchemaBase):
    id: int

    class Config:
        from_attributes = True