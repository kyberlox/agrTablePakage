from pydantic import BaseModel
from typing import Optional, Dict, Any


class SelectedFileSchemaBase(BaseModel):
    name: Optional[str] = None
    result_param_id: int


class SelectedFileSchemaCreate(SelectedFileSchemaBase):
    pass

class SelectedFileSchemaGet(SelectedFileSchemaBase):
    id: int
    parametr_schema_name: Optional[str] = None
    file_path: Optional[str] = None
    file_url: Optional[str] = None

class SelectedFileSchemaUpdate(BaseModel):
    name: Optional[str] = None
    result_param_id: Optional[int] = None


class SelectedFileSchemaResponse(SelectedFileSchemaBase):
    id: int

    class Config:
        from_attributes = True
