import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker


# Загружаем переменные окружения из файла .env
load_dotenv()

# DATABASE_URL = os.getenv("POSTGRESQL_DATABASE_URL")
DATABASE_URL = os.getenv("MYSQL_DATABASE_URL")

# Базовые настройки
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
