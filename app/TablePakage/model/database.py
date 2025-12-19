# app/products/model/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

user = os.getenv('user')
pswd = os.getenv('pswd')
host = os.getenv('DB_HOST', 'postgres')
database = os.getenv('POSTGRES_DB', 'pdb')

engine = create_async_engine(f'postgresql+asyncpg://{user}:{pswd}@{host}/{database}', echo=True)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
