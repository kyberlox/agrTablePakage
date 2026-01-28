# app/products/schema/search.py
from typing import Dict, Optional, List, Any
from pydantic import BaseModel


class ModuleSearchRequest(BaseModel):
    product_id: int
    selected_params: Dict[int, Optional[str]]


class ModuleSearchResponse(BaseModel):
    product_id: int
    product_name: str
    parameters: Dict[str, List[str]]
    matched_rows: int
    request_time: float

    class Config:
        from_attributes = True
