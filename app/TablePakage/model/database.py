# app/products/model/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

user = os.getenv("user")
pswd = os.getenv("pswd")
host = os.getenv("DBHOST", "postgres")
port = os.getenv("POSTGRES_PORT")
database = os.getenv("POSTGRES_DB", "pdb")

def create_async_db_engine():
    max_retries = 5
    retry_delay = 5
    
    for i in range(max_retries):
        try:

            # Используем asyncpg драйвер для асинхронной работы
            engine = create_async_engine(
                f'postgresql+asyncpg://{user}:{pswd}@postgres/pdb',
                pool_size=50,
                max_overflow=0,
                echo=False  # Можно включить для отладки SQL запросов
            )
            print("Асинхронный pSQL движок успешно создан!")
            return engine
        except Exception as e:
            print(f"❌ Async connection attempt {i+1}/{max_retries} failed: {e}")

            if i < max_retries - 1:
                print(f"🕐 Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
    

    print("Failed to create async PostgreSQL engine after multiple attempts")


# engine = create_async_engine(f'postgresql+asyncpg://{user}:{pswd}@{host}:{port}/{database}', echo=True)
engine = create_async_db_engine()

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
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
