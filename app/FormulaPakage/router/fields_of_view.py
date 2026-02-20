from fastapi import APIRouter, HTTPException
import json

router = APIRouter(prefix="/field_of_view", tags=["FieldOfView"])

pattern_file = open("./FormulaPakage/utils/fields_of_view_pattern.json", "r")

FIELDS_OF_VIEW_PATTERN = json.load(pattern_file)

@router.get("/get_all_field_patterns")
async def get_all_field_patterns() -> list[str]:
    return list(FIELDS_OF_VIEW_PATTERN.keys())

@router.get("/get_field_pattern/{pattern}")
async def get_all_field_patterns(pattern: str) -> list[dict]: 
    return FIELDS_OF_VIEW_PATTERN[pattern]['fields']