# app/products/schema/parameter_schema.py
from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any
from ..utils.calculated_utils import OPERATIONS


class ConditionsSchemaBase(BaseModel):
    condition_operator: str
    condition_value: str
    result_value: str
    condition_param_id: int
    result_param_id: int

    @field_validator('condition_operator')
    @classmethod
    def validate_operation(cls, value):
        if value not in OPERATIONS:
            raise ValueError(f"Арифметическая операция: {value} не валидна!")
        return value


class ConditionsSchemaCreate(ConditionsSchemaBase):
    pass


class ConditionsSchemaUpdate(BaseModel):
    condition_operator: Optional[str] = None
    condition_value: Optional[str] = None
    result_value: Optional[str] = None
    condition_param_id: Optional[int] = None
    result_param_id: Optional[int] = None

    @field_validator('condition_operator')
    @classmethod
    def validate_operation(cls, value):
        if value not in OPERATIONS:
            raise ValueError(f"Арифметическая операция: {value} не валидна!")
        return value


class ConditionsSchemaResponse(ConditionsSchemaBase):
    id: int

    class Config:
        from_attributes = True
