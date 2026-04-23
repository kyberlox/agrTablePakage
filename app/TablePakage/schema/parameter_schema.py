# app/products/schema/parameter_schema.py
from pydantic import BaseModel, validator
from typing import Optional, Dict, Any

FIELD_OF_VIEWS = ['user_input', 'calculated', 'conditions', 'selected_file', 'constants']

class ParameterSchemaBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: str  # "Table" or "Formula"
    measuring_unit: Optional[str] = None
    table_name: Optional[str] = None
    visibility: Optional[bool] = True
    required_type: Optional[str] = 'list'
    field_of_view: Optional[Dict[str, bool]] = None
    product_id: int

    @validator('field_of_view', pre=True, always=True)
    def validate_operation(cls, value):
        if value is None:
            return {field: False for field in FIELD_OF_VIEWS}
        if not all(key in FIELD_OF_VIEWS for key in value):
            raise ValueError(f"Недопустимый формульный тип!")
        for field in FIELD_OF_VIEWS:
            if field not in value:
                value[field] = False
        return value


class ParameterSchemaCreate(ParameterSchemaBase):
    pass


class ParameterSchemaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    measuring_unit: Optional[str] = None
    visibility: Optional[bool] = True
    required_type: Optional[str] = 'list'
    table_name: Optional[str] = None
    field_of_view: Optional[Dict[str, bool]] = None
    product_id: Optional[int] = None

    @validator('field_of_view', pre=True, always=True)
    def validate_operation(cls, value):
        if value is None:
            return {field: False for field in FIELD_OF_VIEWS}
        if not all(key in FIELD_OF_VIEWS for key in value):
            raise ValueError(f"Недопустимый формульный тип!")
        for field in FIELD_OF_VIEWS:
            if field not in value:
                value[field] = False
        return value


class ParameterSchemaResponse(ParameterSchemaBase):
    id: int
    transliterated_name: str

    class Config:
        from_attributes = True
