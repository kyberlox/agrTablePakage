from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from .TablePakage.model.product import Product
from .TablePakage.router.products import router as products_router
from .TablePakage.router.parameters import router as parameters_router
from .TablePakage.router.tables import router as tables_router
from .TablePakage.model.database import create_tables, get_db
import app.logging_config
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title=" App API", version="1.0.0")


# Создаём таблицы при старте приложения
@app.on_event("startup")
async def startup_event():
    await create_tables()


# Подключаем статические файлы (для изображений)
# app.mount("/static", StaticFiles(directory="app/products/static"), name="static")
app.mount("/api/files", StaticFiles(directory="./static"), name="files")

# Подключаем роутеры
app.include_router(products_router, prefix="/api")
app.include_router(parameters_router, prefix="/api")
app.include_router(tables_router, prefix="/api")
app.include_router(modules_router, prefix="/api")


@app.get("/")
async def read_root():
    return {"message": "Welcome to App for API"}


# В app/main.py
@app.get("/health")
async def health_check():
    return {"status": "ok"}
