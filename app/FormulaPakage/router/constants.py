from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.TablePakage.model.database import get_db
from app.TablePakage.model.parameter_schema import ParameterSchema

from ..model.constants import Constants
from ..schema.constants_schema import ConstantsSchemaGet, ConstantsSchemaCreate, ConstantsSchemaUpdate, ConstantsSchemaResponse

from .fields_of_view import FIELDS_OF_VIEW_PATTERN

router = APIRouter(prefix="/constants", tags=["Constants"])

@router.get("/get_constants", response_model=List[ConstantsSchemaGet], description="Получение данных о всех Constants параметров")
async def get_constants(db: AsyncSession = Depends(get_db)):
    try:
        res = []
        stmt = select(
            Constants.id,
            Constants.name,
            Constants.description,
            Constants.value,
            Constants.result_param_id,
            ParameterSchema.name.label('parameter_schema_name')
        ).join(
            ParameterSchema, Constants.result_param_id == ParameterSchema.id
        )
        result = await db.execute(stmt)
        constants = result.fetchall()
        if not constants:
            return res
        for constant in constants:
            
            data = {
                'id': constant.id,
                'name': constant.name,
                'description': constant.description,
                'value': constant.value,
                'result_param_id': constant.result_param_id,
                'parameter_schema_name': constant.parameter_schema_name
            }
            res.append(data)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении записей в Constantss: {e}")

@router.get("/get_constant/{id}", description="Получение данных о Constantss по id записи") # response_model=ConstantsSchemaResponse, 
async def get_constant(id: int, db: AsyncSession = Depends(get_db)):
    try:
        res = []
        stmt = select(
            Constants.id,
            Constants.name,
            Constants.description,
            Constants.value,
            Constants.result_param_id,
            ParameterSchema.name.label('parameter_schema_name')
        ).join(
            ParameterSchema, Constants.result_param_id == ParameterSchema.id
        ).where(Constants.id == id)
        result = await db.execute(stmt)
        constant = result.one_or_none()
        if not constant:
            raise HTTPException(status_code=404, detail=f"Отсутствует запись в Constantss с id: {id}")
        constant_result = {'fields': []}
        data = {
            'id': constant.id,
            'name': constant.name,
            'description': constant.description,
            'value': constant.value,
            'result_param_id': constant.result_param_id,
            'parameter_schema_name': constant.parameter_schema_name
        }
        for field in FIELDS_OF_VIEW_PATTERN['constants']['fields']:
            if field['field'] in data and data[field['field']] is not None:
                field['value'] = data[field['field']]
                constant_result['fields'].append(field)
                continue
                
            constant_result['fields'].append(field)

        return constant_result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении записи в Constantss с id = {id}: {e}")

@router.post("/add_constant", description="Создание записи в Constantss") # response_model=ConstantsSchemaResponse, 
async def add__constant(
    schema_create: ConstantsSchemaCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(ParameterSchema).where(ParameterSchema.id == schema_create.result_param_id))
        param = result.scalar_one_or_none()
        if not param:
            raise HTTPException(status_code=404, detail=f"Отсутствует параметр с id: {schema_create.result_param_id}")
        new_node = Constants(**schema_create.model_dump())
        db.add(new_node)
        await db.commit()
        await db.refresh(new_node)

        # Сборка шаблона
        constant_result = {'fields': []}
        data = {
            'id': new_node.id,
            'name': new_node.name,
            'description': new_node.description,
            'value': new_node.value,
            'result_param_id': new_node.result_param_id,
            'parameter_schema_name': param.name
        }
        for field in FIELDS_OF_VIEW_PATTERN['constants']['fields']:
            if field['field'] in data and data[field['field']] is not None:
                field['value'] = data[field['field']]
                constant_result['fields'].append(field)
                continue
                
            constant_result['fields'].append(field)

        return constant_result
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при добавлении параметра с id: {schema_create.result_param_id} в таблицу Constantss: {str(e)}")

@router.put("/update/{node_id}", description="Занесение/обновление данных в таблицу Constantss") # response_model=ConstantsSchemaGet, 
async def update(
    node_id: int,
    schema_update: ConstantsSchemaUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:

        result = await db.execute(select(Constants).where(Constants.id == node_id))
        existing_node = result.scalar_one_or_none()
        if not existing_node:
            raise HTTPException(status_code=404, detail=f"Отсутствует запись в Constants с id: {node_id}")
        

        for key, value in schema_update.dict(exclude_unset=True).items():
            setattr(existing_node, key, value)
        await db.commit()
        await db.refresh(existing_node)

        # Сборка шаблона
        result = await db.execute(select(ParameterSchema).where(ParameterSchema.id == existing_node.result_param_id))
        param = result.scalar_one_or_none()
        if not param:
            raise HTTPException(status_code=404, detail=f"Отсутствует параметр с id: {existing_node.result_param_id}")

        constant_result = {'fields': []}
        data = {
            'id': existing_node.id,
            'name': existing_node.name,
            'description': existing_node.description,
            'value': existing_node.value,
            'result_param_id': existing_node.result_param_id,
            'parameter_schema_name': param.name
        }
        for field in FIELDS_OF_VIEW_PATTERN['constants']['fields']:
            if field['field'] in data and data[field['field']] is not None:
                field['value'] = data[field['field']]
                constant_result['fields'].append(field)
                continue
                
            constant_result['fields'].append(field)

        return constant_result
        # return existing_node
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении записи с id: {node_id} в таблице Constants: {str(e)}")

@router.delete("/delete_node/{node_id}", description="Удаление записи с Constants")   # response_model=ConstantsSchemaResponse, 
async def delete_node(
    node_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(Constants).where(Constants.id == node_id))
        existing_node = result.scalar_one_or_none()
        if not existing_node:
            raise HTTPException(status_code=404, detail=f"Отсутствует запись в Constants с id: {node_id}")
        
        
        await db.delete(existing_node)
        await db.commit()

        return True
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении записи в Constants с id: {node_id}")
