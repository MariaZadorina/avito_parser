from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from database import Base


class TaskStatus(PyEnum):
    IN_PROGRESS = "ОБРАБАТЫВАЕТСЯ"
    COMPLETED = "ВЫПОЛНЕНО"
    ERROR = "ОШИБКА"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)  # Автоинкрементный идентификатор
    sheet_records = relationship("GoogleSheetRecord", back_populates="task")
    external_id = Column(
        String,
        unique=True,
        nullable=True,
    )  # Идентификатор задачи из eshmakar # noqa E501
    link_to_parse = Column(String, index=True)
    created_date = Column(DateTime, default=datetime.utcnow)
    parsed_date = Column(DateTime, nullable=True)
    link_to_google_sheet = Column(String, nullable=True)
    status = Column(
        Enum(TaskStatus),
        default=TaskStatus.IN_PROGRESS,
        index=True,
    )  # Используем перечисление
    title = Column(String, nullable=True)
    has_data_in_db = Column(Boolean, default=False, index=True)
    in_eshmakar_queue = Column(Boolean, default=False)
    # comment = Column(String, nullable=True)
