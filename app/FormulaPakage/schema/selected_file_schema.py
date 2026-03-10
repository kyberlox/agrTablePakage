from pydantic import BaseModel
from typing import Optional, Dict, Any


class SelectedFileSchemaBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parametr_schema_id: int


class SelectedFileSchemaCreate(SelectedFileSchemaBase):
    pass


class SelectedFileSchemaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parametr_schema_id: Optional[int] = None


class SelectedFileSchemaResponse(SelectedFileSchemaBase):
    id: int

    class Config:
        from_attributes = True
