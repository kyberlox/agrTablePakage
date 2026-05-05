# app/TablePakage/routers/code_param.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import aliased

from app.TablePakage.model.database import get_db
from app.TablePakage.model.parameter_schema import ParameterSchema

from ..TablePakage.model.code_param import CodeParam
from ..TablePakage.schema.code_schema import (
    CodeParamCreate,
    CodeParamUpdate,
    CodeParamResponse,
    CodeParamGet
)
from .fields_of_view import FIELDS_OF_VIEW_PATTERN   # предположим, что там есть ключ 'codeparam'


router = APIRouter(prefix="/codeparam", tags=["CodeParam"])


@router.get("/get_codeparams", response_model=List[CodeParamGet])
async def get_codeparams(db: AsyncSession = Depends(get_db)):
    """Получить все записи CodeParam с именами связанных параметров"""
    try:
        ResultParam = aliased(ParameterSchema)
        stmt = select(
            CodeParam.id,
            CodeParam.name,
            CodeParam.description,
            CodeParam.function_name,
            CodeParam.result_param_id,
            ResultParam.name.label("result_param_name")
        ).join(ResultParam, CodeParam.result_param_id == ResultParam.id)

        result = await db.execute(stmt)
        rows = result.all()

        response = []
        for row in rows:
            response.append({
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "function_name": row.function_name,
                "result_param_id": row.result_param_id,
                "result_param_name": row.result_param_name,
            })
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения списка CodeParam: {e}")


@router.get("/get_codeparam/{id}")
async def get_codeparam(id: int, db: AsyncSession = Depends(get_db)):
    """Получить одну запись CodeParam по id (с шаблоном представления)"""
    try:
        ResultParam = aliased(ParameterSchema)
        stmt = select(
            CodeParam.id,
            CodeParam.name,
            CodeParam.description,
            CodeParam.function_name,
            CodeParam.result_param_id,
            ResultParam.name.label("result_param_name")
        ).join(ResultParam, CodeParam.result_param_id == ResultParam.id).where(CodeParam.id == id)

        result = await db.execute(stmt)
        row = result.one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail=f"CodeParam с id {id} не найден")

        data = {
            "id": row.id,
            "name": row.name,
            "description": row.description,
            "function_name": row.function_name,
            "result_param_id": row.result_param_id,
            "result_param_name": row.result_param_name,
        }

        # Формируем ответ по шаблону полей (аналогично Calculated)
        response = {"fields": []}
        for field in FIELDS_OF_VIEW_PATTERN.get("codeparam", {}).get("fields", []):
            field_copy = field.copy()
            if field["field"] in data and data[field["field"]] is not None:
                field_copy["value"] = data[field["field"]]
            response["fields"].append(field_copy)

        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения CodeParam id={id}: {e}")


@router.post("/add_codeparam")
async def add_codeparam(
    schema: CodeParamCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создать новую запись CodeParam"""
    try:
        # Проверяем, существует ли параметр-результат
        result_param = await db.execute(
            select(ParameterSchema).where(ParameterSchema.id == schema.result_param_id)
        )
        if not result_param.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"ParameterSchema id={schema.result_param_id} не найден")

        new_record = CodeParam(**schema.model_dump())
        db.add(new_record)
        await db.commit()
        await db.refresh(new_record)

        # Получаем имя параметра-результата для ответа
        res_name = (await db.execute(
            select(ParameterSchema.name).where(ParameterSchema.id == new_record.result_param_id)
        )).scalar_one()

        data = {
            "id": new_record.id,
            "name": new_record.name,
            "description": new_record.description,
            "function_name": new_record.function_name,
            "result_param_id": new_record.result_param_id,
            "result_param_name": res_name,
        }

        response = {"fields": []}
        for field in FIELDS_OF_VIEW_PATTERN.get("codeparam", {}).get("fields", []):
            field_copy = field.copy()
            if field["field"] in data and data[field["field"]] is not None:
                field_copy["value"] = data[field["field"]]
            response["fields"].append(field_copy)

        return response
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка добавления CodeParam: {e}")


@router.put("/update/{record_id}")
async def update_codeparam(
    record_id: int,
    schema: CodeParamUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновить существующую запись CodeParam"""
    try:
        existing = await db.execute(select(CodeParam).where(CodeParam.id == record_id))
        existing = existing.scalar_one_or_none()
        if not existing:
            raise HTTPException(status_code=404, detail=f"CodeParam id={record_id} не найден")

        # Если изменили result_param_id – проверить существование
        if schema.result_param_id is not None:
            res_param = await db.execute(
                select(ParameterSchema).where(ParameterSchema.id == schema.result_param_id)
            )
            if not res_param.scalar_one_or_none():
                raise HTTPException(status_code=404, detail=f"ParameterSchema id={schema.result_param_id} не найден")

        # Применяем изменения
        for key, value in schema.model_dump(exclude_unset=True).items():
            setattr(existing, key, value)

        await db.commit()
        await db.refresh(existing)

        # Получаем имена для ответа
        res_name = (await db.execute(
            select(ParameterSchema.name).where(ParameterSchema.id == existing.result_param_id)
        )).scalar_one()

        data = {
            "id": existing.id,
            "name": existing.name,
            "description": existing.description,
            "function_name": existing.function_name,
            "result_param_id": existing.result_param_id,
            "result_param_name": res_name,
        }

        response = {"fields": []}
        for field in FIELDS_OF_VIEW_PATTERN.get("codeparam", {}).get("fields", []):
            field_copy = field.copy()
            if field["field"] in data and data[field["field"]] is not None:
                field_copy["value"] = data[field["field"]]
            response["fields"].append(field_copy)

        return response
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка обновления CodeParam id={record_id}: {e}")


@router.delete("/delete/{record_id}", response_model=bool)
async def delete_codeparam(record_id: int, db: AsyncSession = Depends(get_db)):
    """Удалить запись CodeParam"""
    try:
        existing = await db.execute(select(CodeParam).where(CodeParam.id == record_id))
        existing = existing.scalar_one_or_none()
        if not existing:
            raise HTTPException(status_code=404, detail=f"CodeParam id={record_id} не найден")

        await db.delete(existing)
        await db.commit()
        return True
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка удаления CodeParam id={record_id}: {e}")