# app/products/schema/search.py
from typing import Dict, Optional, List, Any, Union
from pydantic import BaseModel


class ModuleSearchRequest(BaseModel):
    product_id: int
    selected_params: Dict[int, Optional[str]]


class ModuleSearchResponse(BaseModel):
    product_id: int
    product_name: str
    # parameters: Dict[str, Union[str, List[str] ]]
    parameters: Optional[List[Dict[str, Any]]] = []
    matched_rows: int
    request_time: float

    class Config:
        from_attributes = True
