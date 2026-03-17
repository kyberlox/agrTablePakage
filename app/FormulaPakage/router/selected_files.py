from fastapi import APIRouter, Depends, HTTPException, UploadFile
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.TablePakage.model.database import get_db
from app.TablePakage.model.parameter_schema import ParameterSchema

from ..model.selected_file import SelectedFile
from ..schema.selected_file_schema import SelectedFileSchemaGet, SelectedFileSchemaCreate, SelectedFileSchemaUpdate, SelectedFileSchemaResponse

from .fields_of_view import FIELDS_OF_VIEW_PATTERN

import aiofiles
import os
from pathlib import Path
import uuid

router = APIRouter(prefix="/selected_file", tags=["SelectedFiles"])

STORAGE_PATH = ("./static/param_files")
os.makedirs(STORAGE_PATH, exist_ok=True)

def generate_unique_filename(original_filename: str) -> str:
    ext = Path(original_filename).suffix
    unique_name = f"{uuid.uuid4()}{ext}"
    return unique_name


@router.put("/update/{node_id}", description="Занесение данных в таблицу") # response_model=SelectedFileSchemaResponse, 
async def update(
    node_id: int,
    schema_update: SelectedFileSchemaUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(SelectedFile).where(SelectedFile.id == node_id))
        existing_node = result.scalar_one_or_none()
        if not existing_node:
            raise HTTPException(status_code=404, detail=f"Отсутствует запись в SelectedFile с id: {node_id}")
        
        for key, value in schema_update.dict(exclude_unset=True).items():
            setattr(existing_node, key, value)
        
        await db.commit()
        await db.refresh(existing_node)

        # Сборка шаблона
        stmt = select(ParameterSchema).where(ParameterSchema.id == existing_node.parametr_schema_id)
        res = await db.execute(stmt)
        param = res.scalar_one_or_none()
        if not param:
            raise HTTPException(status_code=404, detail=f"Отсутствует параметр с id: {existing_node.parametr_schema_id}")
        selected_file_result = {'fields': []}
        data = {
            'id': existing_node.id,
            'file_path': existing_node.file_path,
            'file_url': existing_node.file_url,
            'name': existing_node.name,
            'parametr_schema_name': param.name,
            'parametr_schema_id': param.id
        }
        for field in FIELDS_OF_VIEW_PATTERN['selected_file']['fields']:
            if field['field'] in data and data[field['field']] is not None:
                field['value'] = data[field['field']]
                selected_file_result['fields'].append(field)
                continue
                
            selected_file_result['fields'].append(field)

        return selected_file_result
        # return existing_node
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении записи с id: {node_id} в таблице SelectedFile: {str(e)}")

@router.put("/upload/{node_id}", description="Загрузка файла к параметру")
async def upload(
    node_id: int,
    sel_file: UploadFile,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(SelectedFile).where(SelectedFile.id == node_id))
        existing_node = result.scalar_one_or_none()
        if not existing_node:
            raise HTTPException(status_code=404, detail=f"Отсутствует запись в SelectedFile с id: {node_id}")
        
        file_fromat = sel_file.filename.split('.')[-1]
        chunk_size = 1024 * 1024

        unique_filename = generate_unique_filename(sel_file.filename)

        file_path = os.path.join(STORAGE_PATH, unique_filename)
        file_url = f"/api/files/param_files/{unique_filename}"

        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await sel_file.read(chunk_size):
                await f.write(chunk)

        existing_node.file_path = file_path
        existing_node.file_url = file_url
        existing_node.content_type = file_fromat

        
        await db.commit()
        await db.refresh(existing_node)

        # Сборка шаблона
        stmt = select(ParameterSchema).where(ParameterSchema.id == existing_node.parametr_schema_id)
        res = await db.execute(stmt)
        param = res.scalar_one_or_none()
        if not param:
            raise HTTPException(status_code=404, detail=f"Отсутствует параметр с id: {existing_node.parametr_schema_id}")
        selected_file_result = {'fields': []}
        data = {
            'id': existing_node.id,
            'file_path': existing_node.file_path,
            'file_url': existing_node.file_url,
            'name': existing_node.name,
            'content_type': existing_node.content_type,
            'parametr_schema_name': param.name,
            'parametr_schema_id': param.id
        }
        for field in FIELDS_OF_VIEW_PATTERN['selected_file']['fields']:
            if field['field'] in data and data[field['field']] is not None:
                field['value'] = data[field['field']]
                selected_file_result['fields'].append(field)
                continue
                
            selected_file_result['fields'].append(field)

        return selected_file_result
        # return existing_node
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке файла в запись с id: {node_id} в таблицу SelectedFile: {str(e)}")



@router.post("/add_param/{param_id}", description="Создание записи для загрузки файла")
async def add_param_to_selected_file(param_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(ParameterSchema).where(ParameterSchema.id == param_id))
        param = result.scalar_one_or_none()
        if not param:
            raise HTTPException(status_code=404, detail=f"Отсутствует параметр с id: {param_id}")
        new_node = SelectedFile(parametr_schema_id=param_id)
        db.add(new_node)
        await db.commit()
        await db.refresh(new_node)

        # Сборка шаблона
        selected_file_result = {'fields': []}
        data = {
            'id': new_node.id,
            'file_path': new_node.file_path,
            'file_url': new_node.file_url,
            'content_type': new_node.content_type,
            'name': new_node.name,
            'parametr_schema_name': param.name,
            'parametr_schema_id': param.id
        }
        for field in FIELDS_OF_VIEW_PATTERN['selected_file']['fields']:
            if field['field'] in data and data[field['field']] is not None:
                field['value'] = data[field['field']]
                selected_file_result['fields'].append(field)
                continue
                
            selected_file_result['fields'].append(field)

        return selected_file_result
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при добавлении параметра с id: {param_id} в таблицу SelectedFile: {str(e)}")

@router.delete("/delete_file/{node_id}", description="Удаление файла")  
async def delete_file(
    node_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(SelectedFile).where(SelectedFile.id == node_id))
        existing_node = result.scalar_one_or_none()
        if not existing_node:
            raise HTTPException(status_code=404, detail=f"Отсутствует запись в SelectedFile с id: {node_id}")

        if existing_node.file_path:
            exist_file = os.path.exists(existing_node.file_path)
            if not exist_file:
                raise HTTPException(status_code=404, detail=f"Отсутствует файл в SelectedFile с id: {node_id}")
        
            os.remove(existing_node.file_path)
        existing_node.file_path = None
        existing_node.file_url = None
        existing_node.content_type = None
        
        await db.commit()
        await db.refresh(existing_node)

        # Сборка шаблона
        stmt = select(ParameterSchema).where(ParameterSchema.id == existing_node.parametr_schema_id)
        res = await db.execute(stmt)
        param = res.scalar_one_or_none()
        if not param:
            raise HTTPException(status_code=404, detail=f"Отсутствует параметр с id: {existing_node.parametr_schema_id}")
        selected_file_result = {'fields': []}
        data = {
            'id': existing_node.id,
            'file_path': existing_node.file_path,
            'file_url': existing_node.file_url,
            'name': existing_node.name,
            'parametr_schema_name': param.name,
            'parametr_schema_id': param.id
        }
        for field in FIELDS_OF_VIEW_PATTERN['selected_file']['fields']:
            if field['field'] in data and data[field['field']] is not None:
                field['value'] = data[field['field']]
                selected_file_result['fields'].append(field)
                continue
                
            selected_file_result['fields'].append(field)

        return selected_file_result
        
        # return True
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении файла в SelectedFile с id: {node_id} - {e}")

@router.delete("/delete_node/{node_id}", description="Удаление записи с SelectedFile")  
async def delete_node(
    node_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(SelectedFile).where(SelectedFile.id == node_id))
        existing_node = result.scalar_one_or_none()
        if not existing_node:
            raise HTTPException(status_code=404, detail=f"Отсутствует запись в SelectedFile с id: {node_id}")
        if existing_node.file_path:
            exist_file = os.path.exists(existing_node.file_path)
            if not exist_file:
                raise HTTPException(status_code=404, detail=f"Отсутствует файл в SelectedFile с id: {node_id}")
        
            os.remove(file_path)
            existing_node.file_path = None
        await db.delete(existing_node)
        await db.commit()

        return True
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении записи в SelectedFile с id: {node_id}: {e}")


@router.get("/get_selected_file/{node_id}", description="Получение данных о загруженном файле к параметру")
async def get_selected_file(node_id: int, db: AsyncSession = Depends(get_db)):
    try:
        stmt = select(
            SelectedFile.id,
            SelectedFile.file_path,
            SelectedFile.file_url,
            SelectedFile.name,
            SelectedFile.content_type,
            ParameterSchema.name.label('parametr_schema_name'),
            ParameterSchema.id.label('parametr_schema_id')
        ).join(ParameterSchema).where(SelectedFile.id == node_id, ParameterSchema.id == SelectedFile.parametr_schema_id)
        result = await db.execute(stmt)
        selected_file = result.one_or_none()
        if not selected_file:
            raise HTTPException(status_code=404, detail=f"Отсутствует запись в SelectedFile с id: {node_id}")
        selected_file_result = {'fields': []}
        data = {
            'id': selected_file.id,
            'file_path': selected_file.file_path,
            'file_url': selected_file.file_url,
            'name': selected_file.name,
            'content_type': selected_file.content_type,
            'parametr_schema_name': selected_file.parametr_schema_name,
            'parametr_schema_id': selected_file.parametr_schema_id
        }
        for field in FIELDS_OF_VIEW_PATTERN['selected_file']['fields']:
            if field['field'] in data and data[field['field']] is not None:
                field['value'] = data[field['field']]
                selected_file_result['fields'].append(field)
                continue
                
            selected_file_result['fields'].append(field)

        return selected_file_result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении записи в SelectedFile с id: {node_id}: {e}")

@router.get("/get_selected_files", response_model=List[SelectedFileSchemaGet], description="Получение данных о всех загруженных файлах")
async def get_selected_files(db: AsyncSession = Depends(get_db)):
    try:
        res = []
        stmt = select(
            SelectedFile.id,
            SelectedFile.file_path,
            SelectedFile.file_url,
            SelectedFile.name,
            ParameterSchema.name.label('parametr_schema_name'),
            ParameterSchema.id.label('parametr_schema_id')
        ).join(ParameterSchema).where(ParameterSchema.id == SelectedFile.parametr_schema_id)
        result = await db.execute(stmt)
        selected_files = result.fetchall()
        if not selected_files:
            return res
        for files in selected_files:
            data = {
                'id': files.id,
                'file_path': files.file_path,
                'file_url': files.file_url,
                'name': files.name,
                'parametr_schema_name': files.parametr_schema_name,
                'parametr_schema_id': files.parametr_schema_id
            }
            res.append(data)
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении записей в SelectedFile: {e}")
