import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker


# Загружаем переменные окружения из файла .env
load_dotenv()

DATABASE_URL = os.getenv("POSTGRESQL_DATABASE_URL")

# Базовые настройки
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создание всех таблиц в базе данных
Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Базовый класс для MySQL
# MySQLBase = declarative_base()
# mysql_engine = create_engine(MYSQL_DATABASE_URL)
# MySQLSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=mysql_engine)
# MySQLBase.metadata.create_all(bind=mysql_engine)

# def get_mysql_db():
#     db = MySQLSessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
