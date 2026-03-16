from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import aliased

from app.TablePakage.model.database import get_db
from app.TablePakage.model.parameter_schema import ParameterSchema

from ..model.calculated import Calculated
from ..schema.calculated_schema import CalculatedSchemaCreate, CalculatedSchemaUpdate, CalculatedSchemaResponse, CalculatedSchemaGet

from .fields_of_view import FIELDS_OF_VIEW_PATTERN

router = APIRouter(prefix="/calculated", tags=["Calculated"])

@router.get("/get_calculates", response_model=List[CalculatedSchemaGet], description="Получение данных о всех Calculated параметров")
async def get_calculates(db: AsyncSession = Depends(get_db)):
    try:
        FirstParameter = aliased(ParameterSchema)
        SecondParameter = aliased(ParameterSchema)
        ResultParameter = aliased(ParameterSchema)
        res = []
        stmt = select(
            Calculated.id,
            Calculated.name,
            Calculated.description,
            Calculated.operation,
            Calculated.parameter_1_id,
            Calculated.parameter_2_id,
            Calculated.result_param_id,
            FirstParameter.name.label('parameter_1_name'),
            SecondParameter.name.label('parameter_2_name'),
            ResultParameter.name.label('result_param_name')
        ).join(
            FirstParameter, Calculated.parameter_1_id == FirstParameter.id, isouter = True
        ).join(
            ResultParameter, Calculated.result_param_id == ResultParameter.id
        ).join(
            SecondParameter, Calculated.parameter_2_id == SecondParameter.id, isouter = True
        )
        result = await db.execute(stmt)
        calculates = result.fetchall()
        
        if not calculates:
            return res
        for calculate in calculates:
            data = {
                'id': calculate.id,
                'name': calculate.name,
                'description': calculate.description,
                'operation': calculate.operation,
                'parameter_1_id': calculate.parameter_1_id,
                'parameter_1_name': calculate.parameter_1_name,
                'parameter_2_id': calculate.parameter_2_id,
                'parameter_2_name': calculate.parameter_2_name,
                'result_param_id': calculate.result_param_id,
                'result_param_name': calculate.result_param_name
            }
            res.append(data)
        return res
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при получении записей в Calculated: {e}")

@router.get("/get_calculate/{id}", description="Получение данных о Calculated по id записи") # , response_model=CalculatedSchemaGet
async def get_calculate(id: int, db: AsyncSession = Depends(get_db)):
    try:
        FirstParameter = aliased(ParameterSchema)
        SecondParameter = aliased(ParameterSchema)
        ResultParameter = aliased(ParameterSchema)
        res = []
        stmt = select(
            Calculated.id,
            Calculated.name,
            Calculated.description,
            Calculated.operation,
            Calculated.parameter_1_id,
            Calculated.parameter_2_id,
            Calculated.result_param_id,
            FirstParameter.name.label('parameter_1_name'),
            SecondParameter.name.label('parameter_2_name'),
            ResultParameter.name.label('result_param_name')
        ).join(
            FirstParameter, Calculated.parameter_1_id == FirstParameter.id, isouter = True
        ).join(
            ResultParameter, Calculated.result_param_id == ResultParameter.id
        ).join(
            SecondParameter, Calculated.parameter_2_id == SecondParameter.id, isouter = True
        ).where(Calculated.id == id)
        result = await db.execute(stmt)
        calculate = result.one_or_none()
        if not calculate:
            raise HTTPException(status_code=404, detail=f"Отсутствует запись в Calculate с id: {id}")
        calculate_result = {'fields': []}
        data = {
            'id': calculate.id,
            'name': calculate.name,
            'description': calculate.description,
            'operation': calculate.operation,
            'parameter_1_id': calculate.parameter_1_id,
            'parameter_1_name': calculate.parameter_1_name,
            'parameter_2_id': calculate.parameter_2_id,
            'parameter_2_name': calculate.parameter_2_name,
            'result_param_id': calculate.result_param_id,
            'result_param_name': calculate.result_param_name
        }
        for field in FIELDS_OF_VIEW_PATTERN['calculated']['fields']:
            if field['field'] in data and data[field['field']] is not None:
                field['value'] = data[field['field']]
                calculate_result['fields'].append(field)
                continue
                
            calculate_result['fields'].append(field)

        return calculate_result
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при получении записи в Calculate с id = {id}: {e}")

@router.post("/add_param/{param_id}", description="Создание записи в Calculated") # response_model=Dict['str', List[CalculatedSchemaResponse]], 
async def add_param_to_condition(param_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(ParameterSchema).where(ParameterSchema.id == param_id))
        param = result.scalar_one_or_none()
        if not param:
            raise HTTPException(status_code=404, detail=f"Отсутствует параметр с id: {param_id}")
        new_node = Calculated(result_param_id=param_id)
        db.add(new_node)
        await db.commit()
        await db.refresh(new_node)
        
        # Сборка шаблона
        calculated_result = {'fields': []}
        data = {
            'id': new_node.id,
            'name': new_node.name,
            'description': new_node.description,
            'operation': new_node.operation,
            'parameter_1_id': new_node.parameter_1_id,
            'parameter_2_id': new_node.parameter_2_id,
            'result_param_id': new_node.result_param_id,
            'result_param_name': param.name
        }
        
        for field in FIELDS_OF_VIEW_PATTERN['calculated']['fields']:
            if field['field'] in data and data[field['field']] is not None:
                field['value'] = data[field['field']]
                calculated_result['fields'].append(field)
                continue
                
            calculated_result['fields'].append(field)
        
        return calculated_result
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при добавлении параметра с id: {param_id} в таблицу Calculated: {str(e)}")

@router.put("/update/{node_id}", description="Занесение/обновление данных в таблицу Calculated") # response_model=CalculatedSchemaResponse, 
async def update(
    node_id: int,
    schema_update: CalculatedSchemaUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        FirstParameter = aliased(ParameterSchema)
        SecondParameter = aliased(ParameterSchema)
        ResultParameter = aliased(ParameterSchema)

        result = await db.execute(select(Calculated).where(Calculated.id == node_id))
        existing_node = result.scalar_one_or_none()
        if not existing_node:
            raise HTTPException(status_code=404, detail=f"Отсутствует запись в Calculated с id: {node_id}")
        
        # ДОБАВИТЬ РАСЧЕТ result_value И ЗАНЕСТИ В ТАБЛИЦУ

        for key, value in schema_update.dict(exclude_unset=True).items():
            setattr(existing_node, key, value)
        
        await db.commit()
        await db.refresh(existing_node)

        # Сборка шаблона
        stmt = select(
            FirstParameter.name.label('parameter_1_name'),
            SecondParameter.name.label('parameter_2_name'), 
            ResultParameter.name.label('result_param_name')
        ).select_from(Calculated).join(
            FirstParameter, FirstParameter.id == existing_node.parameter_1_id
        ).join(
            SecondParameter, SecondParameter.id == existing_node.parameter_2_id
        ).join(
            ResultParameter, ResultParameter.id == existing_node.result_param_id
        ).where(Calculated.id == existing_node.id)
        res = await db.execute(stmt)
        params = res.first()
        
        if not params:
            raise HTTPException(status_code=404, detail=f"Отсутствует один из параметров в ParameterSchema: {existing_node.parameter_1_id}, {existing_node.parameter_2_id},{existing_node.result_param_id}")
        calculate_result = {'fields': []}

        parameter_1_name, parameter_2_name, result_param_name = params

        data = {
            'id': existing_node.id,
            'name': existing_node.name,
            'description': existing_node.description,
            'operation': existing_node.operation,
            'parameter_1_id': existing_node.parameter_1_id,
            'parameter_1_name': parameter_1_name,
            'parameter_2_id': existing_node.parameter_2_id,
            'parameter_2_name': parameter_2_name,
            'result_param_id': existing_node.result_param_id,
            'result_param_name': result_param_name
        }
        for field in FIELDS_OF_VIEW_PATTERN['calculated']['fields']:
            if field['field'] in data and data[field['field']] is not None:
                field['value'] = data[field['field']]
                calculate_result['fields'].append(field)
                continue
                
            calculate_result['fields'].append(field)

        return calculate_result
        # return existing_node
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении записи с id: {node_id} в таблице Calculated: {str(e)}")

@router.delete("/delete_node/{node_id}", response_model=CalculatedSchemaResponse, description="Удаление записи с Calculated")  
async def delete_node(
    node_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(Calculated).where(Calculated.id == node_id))
        existing_node = result.one_or_none()
        if not existing_node:
            raise HTTPException(status_code=404, detail=f"Отсутствует запись в Calculated с id: {node_id}")
        
        
        await db.delete(existing_node)
        await db.commit()

        return True
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении записи в Calculated с id: {node_id}")
