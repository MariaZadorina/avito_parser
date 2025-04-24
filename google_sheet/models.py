import hashlib
import json
from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy.orm import relationship

from database import Base


class GoogleSheetRecord(Base):
    __tablename__ = "google_sheet_records"

    id = Column(Integer, primary_key=True)
    source_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    task = relationship("Task", back_populates="sheet_records")
    sheet_id = Column(String(512), index=True)
    row_data = Column(JSON)  # Хранение всей строки как JSON
    row_hash = Column(String(64), unique=True, nullable=False)  # SHA-256 хеш
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Составной индекс для часто используемых запросов
    table_args = (Index("ix_sheet_row", "sheet_id", "row_hash", unique=True),)

    @classmethod
    def create_row_hash(cls, row_data: dict) -> str:
        """Генерирует хеш строки данных"""
        # Сортируем ключи для стабильности хеша
        sorted_data = json.dumps(row_data, sort_keys=True)
        return hashlib.sha256(sorted_data.encode()).hexdigest()
