from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from .TablePakage.router.products import router as products_router
from .TablePakage.router.parameters import router as parameters_router
from .TablePakage.router.tables import router as tables_router
from .TableSearch.router.module_search import router as module_search_router
from .TableSearch.router.module_search_pandas import router as module_search_router_pandas

from .TablePakage.model.database import create_tables
import app.logging_config

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
app.include_router(module_search_router, prefix="/api")
app.include_router(module_search_router_pandas, prefix="/api")


@app.get("/")
async def read_root():
    return {"message": "Welcome to App for API"}


# В app/main.py
@app.get("/health")
async def health_check():
    return {"status": "ok"}
