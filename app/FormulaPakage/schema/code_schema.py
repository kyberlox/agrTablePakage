# app/TablePakage/schema/code_param_schema.py
from pydantic import BaseModel, field_validator
from typing import Optional
from ..utils.code_mode import ALLOWED_FUNCTIONS

class CodeParamBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    function_name: Optional[str] = None
    result_param_id: int

    @field_validator('function_name')
    @classmethod
    def validate_function(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ALLOWED_FUNCTIONS:
            raise ValueError(f"Недопустимое имя функции: {v}. Разрешённые: {ALLOWED_FUNCTIONS}")
        return v

class CodeParamCreate(CodeParamBase):
    pass

class CodeParamGet(CodeParamBase):
    id: int
    result_param_name: Optional[str] = None   # имя параметра-результата

class CodeParamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    function_name: Optional[str] = None
    result_param_id: Optional[int] = None

    @field_validator('function_name')
    @classmethod
    def validate_function(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ALLOWED_FUNCTIONS:
            raise ValueError(f"Недопустимое имя функции: {v}")
        return v

class CodeParamResponse(CodeParamBase):
    id: int

    class Config:
        from_attributes = True