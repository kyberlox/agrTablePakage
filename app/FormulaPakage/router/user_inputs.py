from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.TablePakage.model.database import get_db
from app.TablePakage.model.parameter_schema import ParameterSchema

from ..model.user_input import UserInput
from ..schema.user_input_schema import UserInputSchemaCreate, UserInputSchemaUpdate, UserInputSchemaResponse

router = APIRouter(prefix="/user_input", tags=["UserInputs"])

@router.get("/get_user_inputs", response_model=List[UserInputSchemaResponse], description="Получение данных о всех UserInputs параметров")
async def get_user_inputs(db: AsyncSession = Depends(get_db)):
    try:
        res = []
        stmt = select(
            UserInput.id,
            UserInput.name,
            UserInput.description,
            UserInput.min_value,
            UserInput.max_value,
            UserInput.parameter_schema_id,
            ParameterSchema.name.label('parameter_schema_name')
        ).join(
            ParameterSchema, UserInput.parameter_schema_id == ParameterSchema.id
        )
        result = await db.execute(stmt)
        user_inputs = result.scalars().all()
        if not user_inputs:
            return res
        for user_input in user_inputs:
            data = {
                'id': user_input.id,
                'name': user_input.name,
                'description': user_input.description,
                'type': user_input.type,
                'min_value': user_input.min_value,
                'max_value': user_input.max_value,
                'parameter_schema_id': user_input.parameter_schema_id,
                'parameter_schema_name': user_input.parameter_schema_name
            }
            res.append(data)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении записей в UserInputs: {e}")

@router.get("/get_user_input/{id}", response_model=UserInputSchemaResponse, description="Получение данных о UserInputs по id записи")
async def get_user_input(id: int, db: AsyncSession = Depends(get_db)):
    try:
        res = []
        stmt = select(
            UserInput.id,
            UserInput.name,
            UserInput.description,
            UserInput.type,
            UserInput.min_value,
            UserInput.max_value,
            UserInput.parameter_schema_id,
            ParameterSchema.name.label('parameter_schema_name')
        ).join(
            ParameterSchema, UserInput.parameter_schema_id == ParameterSchema.id
        ).where(UserInput.id == id)
        result = await db.execute(stmt)
        user_input = result.one_or_none()
        if not user_input:
            raise HTTPException(status_code=404, detail=f"Отсутствует запись в UserInputs с id: {id}")
        user_input_result = {'fields': []}
        data = {
            'id': user_input.id,
            'name': user_input.name,
            'description': user_input.description,
            'type': user_input.type,
            'min_value': user_input.min_value,
            'max_value': user_input.max_value,
            'parameter_schema_id': user_input.parameter_schema_id,
            'parameter_schema_name': user_input.parameter_schema_name
        }
        for field in FIELDS_OF_VIEW_PATTERN['user_input']['fields']:
            if field['field'] in data and data[field['field']] is not None:
                field['value'] = data[field['field']]
                user_input_result['fields'].append(field)
                continue
                
            user_input_result['fields'].append(field)

        return user_input_result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении записи в UserInputs с id = {id}: {e}")

@router.post("/add_param/{param_id}", response_model=UserInputSchemaResponse, description="Создание записи в UserInputs")
async def add_param_to_condition(param_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(ParameterSchema).where(ParameterSchema.id == param_id))
        param = result.one_or_none()
        if not param:
            raise HTTPException(status_code=404, detail=f"Отсутствует параметр с id: {param_id}")
        new_node = UserInput(parameter_schema_id=param_id)
        db.add(new_node)
        await db.commit()
        await db.refresh(new_node)

        # Сборка шаблона
        user_input_result = {'fields': []}
        data = {
            'id': user_input.id,
            'name': user_input.name,
            'description': user_input.description,
            'type': user_input.type,
            'min_value': user_input.min_value,
            'max_value': user_input.max_value,
            'parameter_schema_id': user_input.parameter_schema_id,
            'parameter_schema_name': param.name
        }
        for field in FIELDS_OF_VIEW_PATTERN['selected_file']['fields']:
            if field['field'] in data and data[field['field']] is not None:
                field['value'] = data[field['field']]
                user_input_result['fields'].append(field)
                continue
                
            user_input_result['fields'].append(field)

        return user_input_result
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при добавлении параметра с id: {param_id} в таблицу Calculated: {str(e)}")

@router.put("/update/{node_id}", response_model=UserInputSchemaResponse, description="Занесение/обновление данных в таблицу UserInputs")
async def update(
    node_id: int,
    schema_update: UserInputSchemaUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:

        result = await db.execute(select(UserInput).where(UserInput.id == node_id))
        existing_node = result.one_or_none()
        if not existing_node:
            raise HTTPException(status_code=404, detail=f"Отсутствует запись в UserInput с id: {node_id}")
        

        for key, value in schema_update.dict(exclude_unset=True).items():
            setattr(existing_node, key, value)
        await db.refresh(existing_node)
        await db.commit()

        # Сборка шаблона
        result = await db.execute(select(ParameterSchema).where(ParameterSchema.id == existing_node.parameter_schema_id))
        param = result.one_or_none()
        if not param:
            raise HTTPException(status_code=404, detail=f"Отсутствует параметр с id: {existing_node.parameter_schema_id}")

        user_input_result = {'fields': []}
        data = {
            'id': existing_node.id,
            'name': existing_node.name,
            'description': existing_node.description,
            'type': existing_node.type,
            'min_value': existing_node.min_value,
            'max_value': existing_node.max_value,
            'parameter_schema_id': existing_node.parameter_schema_id,
            'parameter_schema_name': param.name
        }
        for field in FIELDS_OF_VIEW_PATTERN['selected_file']['fields']:
            if field['field'] in data and data[field['field']] is not None:
                field['value'] = data[field['field']]
                user_input_result['fields'].append(field)
                continue
                
            user_input_result['fields'].append(field)

        return user_input_result
        # return existing_node
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении записи с id: {node_id} в таблице UserInput: {str(e)}")

@router.delete("/delete_node/{node_id}", response_model=UserInputSchemaResponse, description="Удаление записи с UserInput")  
async def delete_node(
    node_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(UserInput).where(UserInput.id == node_id))
        existing_node = result.one_or_none()
        if not existing_node:
            raise HTTPException(status_code=404, detail=f"Отсутствует запись в UserInput с id: {node_id}")
        
        
        await db.delete(existing_node)
        await db.commit()

        return True
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении записи в UserInput с id: {node_id}")
