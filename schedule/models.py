from datetime import datetime
from datetime import timedelta

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String

from database import Base


class TaskSchedule(Base):
    __tablename__ = "task_schedules"

    id = Column(Integer, primary_key=True)
    task_name = Column(String(100), unique=True)  # Например: "sync_google_sheets"
    description = Column(String(300))
    interval_minutes = Column(Integer, default=60)  # Интервал в минутах
    is_active = Column(Boolean, default=True)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)

    def update_next_run(self):
        """Обновляет значение next_run на основе last_run и interval_minutes"""
        if self.last_run is not None:
            self.next_run = self.last_run + timedelta(minutes=self.interval_minutes)
        else:
            # Если last_run еще не установлен, устанавливаем next_run на текущее время
            self.next_run = datetime.now() + timedelta(minutes=self.interval_minutes)
