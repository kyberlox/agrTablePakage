from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any
from ..utils.calculated_utils import OPERATIONS


class CalculatedSchemaBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    operation: Optional[str] = None 
    parameter_id: Optional[int] = None
    result_param_id: int

    @field_validator('operation')
    @classmethod
    def validate_operation(cls, value):
        if value is not None and value not in OPERATIONS:
            raise ValueError(f"Арифметическая операция: {value} не валидна!")
        return value

class CalculatedSchemaCreate(CalculatedSchemaBase):
    pass

class CalculatedSchemaGet(CalculatedSchemaBase):
    id: int
    parameter_name: Optional[str] = None 
    result_param_name: Optional[str] = None 

class CalculatedSchemaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    operation: Optional[str] = None
    parameter_id: Optional[int] = None
    result_param_id: Optional[int] = None

    @field_validator('operation')
    @classmethod
    def validate_operation(cls, value):
        if value not in OPERATIONS:
            raise ValueError(f"Арифметическая операция: {value} не валидна!")
        return value


class CalculatedSchemaResponse(CalculatedSchemaBase):
    id: int

    class Config:
        from_attributes = True
