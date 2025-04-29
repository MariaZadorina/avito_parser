import os
from sqlalchemy import Column, Integer, String
from database import Base, SessionLocal


class Settings(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    start_time = Column(Integer, nullable=False, default=21)
    eshmakar_api_token = Column(String(255), nullable=False, default="")
    eshmakar_count_of_page_to_parse = Column(Integer, nullable=False, default=1)

    @classmethod
    def _get_settings(cls, db):
        """Внутренний метод с обработкой отсутствия таблицы"""
        try:
            return db.query(cls).first()
        except Exception as e:
            print(f"Error accessing settings table: {e}")
            return None

    @classmethod
    def get_count_of_page_to_parse(cls):
        """Получает количество страниц для парсинга"""
        db = SessionLocal()
        try:
            settings = cls._get_settings(db)
            if settings and settings.eshmakar_count_of_page_to_parse is not None:
                return settings.eshmakar_count_of_page_to_parse
            return int(os.getenv("ESHMAKAR_COUNT_OF_PAGE_TO_PARSE", 1))
        finally:
            db.close()

    @classmethod
    def get_eshmakar_api_token(cls):
        """Получает API токен"""
        db = SessionLocal()
        try:
            settings = cls._get_settings(db)
            if settings and settings.eshmakar_api_token:
                return settings.eshmakar_api_token
            return os.getenv("ESHMAKAR_API_TOKEN", "")
        finally:
            db.close()

    @classmethod
    def get_start_time(cls):
        """Получает время начала работы"""
        db = SessionLocal()
        try:
            settings = cls._get_settings(db)
            if settings and settings.start_time is not None:
                return settings.start_time
            return int(os.getenv("START_TIME", 21))
        finally:
            db.close()