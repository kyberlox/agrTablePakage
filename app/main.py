from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .TablePakage.router.products import router as products_router
from .TablePakage.model.database import create_tables
import app.logging_config

app = FastAPI(title=" App API", version="1.0.0")

# Создаём таблицы при старте приложения
@app.on_event("startup")
async def startup_event():
    await create_tables()

# Подключаем статические файлы (для изображений)
#app.mount("/static", StaticFiles(directory="app/products/static"), name="static")
app.mount("/api/files", StaticFiles(directory="./static"), name="files")

# Подключаем роутеры
app.include_router(products_router, prefix="/api")

@app.get("/")
async def read_root():
    return {"message": "Welcome to App for API"}

# В app/main.py
@app.get("/health")
async def health_check():
    return {"status": "ok"}
