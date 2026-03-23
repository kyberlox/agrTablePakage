# app/products/schema/parameter_schema.py
from pydantic import BaseModel
from typing import Optional, Dict, Any


class UserInputSchemaBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: str
    min_value: float
    max_value: float
    result_param_id: int


class UserInputSchemaCreate(UserInputSchemaBase):
    pass

class UserInputSchemaGet(UserInputSchemaBase):
    id: int
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    # parametr_schema_id: Optional[int] = None
    parameter_schema_name: Optional[str] = None


class UserInputSchemaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    result_param_id: Optional[int] = None


class UserInputSchemaResponse(UserInputSchemaBase):
    id: int

    class Config:
        from_attributes = True