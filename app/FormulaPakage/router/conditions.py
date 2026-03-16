from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import aliased

from app.TablePakage.model.database import get_db
from app.TablePakage.model.parameter_schema import ParameterSchema

from ..model.condition import Conditions
from ..schema.condition_schema import ConditionsSchemaGet, ConditionsSchemaCreate, ConditionsSchemaUpdate, ConditionsSchemaResponse

from .fields_of_view import FIELDS_OF_VIEW_PATTERN

router = APIRouter(prefix="/condition", tags=["Conditions"])

@router.get("/get_conditions", response_model=List[ConditionsSchemaGet], description="Получение данных о всех Conditions") 
async def get_conditions(db: AsyncSession = Depends(get_db)) -> list:
    try:
        ConditionParameter = aliased(ParameterSchema)
        ResultParameter = aliased(ParameterSchema)
        res = []
        stmt = select(
            Conditions.id,
            Conditions.condition_operator,
            Conditions.condition_value,
            Conditions.result_value,
            Conditions.result_param_id,
            Conditions.condition_param_id,
            ConditionParameter.name.label('condition_param_name'),
            ResultParameter.name.label('result_param_name')
        ).join(ConditionParameter, Conditions.condition_param_id == ConditionParameter.id).join(ResultParameter, Conditions.result_param_id == ResultParameter.id)
        result = await db.execute(stmt)
        conditions = result.fetchall()
        if not conditions:
            return res
        for condition in conditions:
            data = {
                'id': condition.id,
                'condition_operator': condition.condition_operator,
                'condition_value': condition.condition_value,
                'result_value': condition.result_value,
                'result_param_id': condition.result_param_id,
                'result_param_name': condition.result_param_name,
                'condition_param_id': condition.condition_param_id,
                'condition_param_name': condition.condition_param_name
            }
            res.append(data)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении записей в Conditions: {e}")

@router.get("/get_condition/{id}", response_model=ConditionsSchemaGet, description="Получение данных о Condition по id записи")
async def get_condition(id: int, db: AsyncSession = Depends(get_db)):
    try:
        ConditionParameter = aliased(ParameterSchema)
        ResultParameter = aliased(ParameterSchema)
        stmt = select(
            Conditions.id,
            Conditions.condition_operator,
            Conditions.condition_value,
            Conditions.result_value,
            Conditions.result_param_id,
            Conditions.condition_param_id,
            ConditionParameter.name.label('condition_param_name'),
            ResultParameter.name.label('result_param_name')
        ).join(ConditionParameter, Conditions.condition_param_id == ConditionParameter.id).join(
            ResultParameter, Conditions.result_param_id == ResultParameter.id).where(
                Conditions.id == id
            )
        result = await db.execute(stmt)
        condition = result.scalar_one_or_none()
        if not condition:
            raise HTTPException(status_code=404, detail=f"Отсутствует запись в Conditions с id: {id}")
        condition_result = {'fields': []}
        data = {
            'id': condition.id,
            'condition_operator': condition.condition_operator,
            'condition_value': condition.condition_value,
            'result_value': condition.result_value,
            'result_param_id': condition.result_param_id,
            'result_param_name': condition.result_param_name,
            'condition_param_id': condition.condition_param_id,
            'condition_param_name': condition.condition_param_name
        }
        for field in FIELDS_OF_VIEW_PATTERN['condition']['fields']:
            if field['field'] in data and data[field['field']] is not None:
                field['value'] = data[field['field']]
                condition_result['fields'].append(field)
                continue
                
            condition_result['fields'].append(field)

        return condition_result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении записи в Conditions с id={id}: {e}")

@router.post("/add_param/{param_id}", description="Создание записи в Conditions") # response_model=ConditionsSchemaResponse, 
async def add_param_to_condition(param_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(ParameterSchema).where(ParameterSchema.id == param_id))
        param = result.scalar_one_or_none()
        if not param:
            raise HTTPException(status_code=404, detail=f"Отсутствует параметр с id: {param_id}")
        new_node = Conditions(result_param_id=param_id)
        db.add(new_node)
        await db.commit()
        await db.refresh(new_node)

        # Сборка шаблона
        condition_result = {'fields': []}
        data = {
            'id': new_node.id,
            'condition_operator': new_node.condition_operator,
            'condition_value': new_node.condition_value,
            'result_value': new_node.result_value,
            'result_param_id': new_node.result_param_id,
            'result_param_name': param.result_param_name
        }
        for field in FIELDS_OF_VIEW_PATTERN['condition']['fields']:
            if field['field'] in data and data[field['field']] is not None:
                field['value'] = data[field['field']]
                condition_result['fields'].append(field)
                continue
                
            condition_result['fields'].append(field)

        return condition_result
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при добавлении параметра с id: {param_id} в таблицу Conditions: {str(e)}")

@router.put("/update/{node_id}", description="Занесение/обновление данных в таблицу") # response_model=ConditionsSchemaResponse, 
async def update(
    node_id: int,
    schema_update: ConditionsSchemaUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        ConditionParameter = aliased(ParameterSchema)
        ResultParameter = aliased(ParameterSchema)

        result = await db.execute(select(Conditions).where(Conditions.id == node_id))
        existing_node = result.scalar_one_or_none()
        if not existing_node:
            raise HTTPException(status_code=404, detail=f"Отсутствует запись в Conditions с id: {node_id}")
        
        # result_value мы получаем

        for key, value in schema_update.dict(exclude_unset=True).items():
            setattr(existing_node, key, value)
        await db.commit()
        await db.refresh(existing_node)

        # Сборка шаблона
        stmt = select(
            ConditionParameter.name.label('condition_param_name'), ResultParameter.name.label('result_param_name')
        ).join(ConditionParameter, ConditionParameter.id == existing_node.condition_param_id).join(ResultParameter, ResultParameter.id == existing_node.result_param_id)
        res = await db.execute(stmt)
        param = res.scalar_one_or_none()
        if not param:
            raise HTTPException(status_code=404, detail=f"Отсутствует параметр с id: {existing_node.parametr_schema_id}")
        condition_result = {'fields': []}
        data = {
            'id': existing_node.id,
            'condition_operator': existing_node.condition_operator,
            'condition_value': existing_node.condition_value,
            'result_value': existing_node.result_value,
            'result_param_id': existing_node.result_param_id,
            'result_param_name': param.result_param_name,
            'condition_param_id': existing_node.condition_param_id,
            'condition_param_name': param.condition_param_name
        }
        for field in FIELDS_OF_VIEW_PATTERN['condition']['fields']:
            if field['field'] in data and data[field['field']] is not None:
                field['value'] = data[field['field']]
                condition_result['fields'].append(field)
                continue
                
            condition_result['fields'].append(field)

        return condition_result
        # return existing_node
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении записи с id: {node_id} в таблице Conditions: {str(e)}")

@router.delete("/delete_node/{node_id}", description="Удаление записи с Conditions")   # response_model=ConditionsSchemaResponse, 
async def delete_node(
    node_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(Conditions).where(Conditions.id == node_id))
        existing_node = result.scalar_one_or_none()
        if not existing_node:
            raise HTTPException(status_code=404, detail=f"Отсутствует запись в Conditions с id: {node_id}")
        
        
        await db.delete(existing_node)
        await db.commit()

        return True
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении записи в Conditions с id: {node_id}")
