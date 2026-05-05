from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
#from .TablePakage.model.product import Product
from .FormulaPakage.model import *

from .TablePakage.router.products import router as products_router
from .TablePakage.router.parameters import router as parameters_router
from .TablePakage.router.tables import router as tables_router
from .TablePakage.router.parameter_values import router as parameter_values_router
from .TableSearch.router.module_search import router as module_search_router
from .TableSearch.router.module_search_pandas import router as module_search_router_pandas

from .TablePakage.model.database import create_tables
import app.logging_config
from .TablePakage.model.database import create_tables

from .FormulaPakage.router.calculate import router as calculated_router
from .FormulaPakage.router.user_inputs import router as user_input_router
from .FormulaPakage.router.conditions import router as condition_router
from .FormulaPakage.router.selected_files import router as selected_file_router
from .FormulaPakage.router.fields_of_view import router as fields_of_view_router
from .FormulaPakage.router.constants import router as constants_router
from .FormulaPakage.router.code_param import router as code_router

# from .TablePakage.router.formulas import router as formulas_router

# import app.logging_config

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dotenv import load_dotenv

load_dotenv()



app = FastAPI(
    title="SaveOfConf API",
    version="1.0.0",
    docs_url="/api/docs", #None
    openapi_url="/api/openapi.json"
)



# # Настройка CORS
origins = ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # В продакшене укажите конкретные домены
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
app.include_router(parameter_values_router, prefix="/api")
app.include_router(module_search_router, prefix="/api")
app.include_router(module_search_router_pandas, prefix="/api")

app.include_router(calculated_router, prefix="/api")
app.include_router(user_input_router, prefix="/api")
app.include_router(condition_router, prefix="/api")
app.include_router(selected_file_router, prefix="/api")
app.include_router(fields_of_view_router, prefix="/api")
app.include_router(constants_router, prefix="/api")

app.include_router(code_router, prefix="/api")



# app.include_router(formulas_router, prefix="/api")



@app.get("/")
async def read_root():
    return {"message": "Welcome to App for API"}


# В app/main.py
@app.get("/health")
async def health_check():
    return {"status": "ok"}
