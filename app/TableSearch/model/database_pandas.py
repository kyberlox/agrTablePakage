import os
from sqlalchemy import create_engine


user = os.getenv("user")
pswd = os.getenv("pswd")
host = os.getenv("DBHOST", "postgres")
port = os.getenv("POSTGRES_PORT")
database = os.getenv("POSTGRES_DB", "pdb")

SYNC_DATABASE_URL = (
    f"postgresql://{user}:{pswd}@{host}:{port}/{database}"
)

sync_engine = create_engine(SYNC_DATABASE_URL)
