import logging
from datetime import datetime
from datetime import timedelta

from sqlalchemy.orm import Session

from schedule.models import TaskSchedule

logger = logging.getLogger(__name__)

DEFAULT_SCHEDULES = [
    {
        "task_name": "enqueue_one_task_for_parsing",
        "description": "Постановка задачи в очередь на парсинг в eshmakar",
        "interval_minutes": 5,
        "is_active": True,
    },
    {
        "task_name": "update_last_task_status_from_eshmakar",
        "description": "Обновление статуса последней задачи на основе данных из eshmakar API, "
        "получение гугл таблицы с данными парсинга",
        "interval_minutes": 7,
        "is_active": True,
    },
    {
        "task_name": "fetch_and_process_sheets",
        "description": "Обрабатывает Google Sheets из Task, которые еще не были загружены в БД, "
        "сохраняет данные из гугл таблицы в базу",
        "interval_minutes": 9,
        "is_active": True,
    },
    {
        "task_name": "reset_daily_tasks",
        "description": "Сброс статусов задач в START_TIME каждый день. ",
        "interval_minutes": 10,
        "is_active": True,
    },
]


def init_default_schedules(db: Session):
    """Инициализирует таблицу task_schedules стандартными значениями"""
    try:
        if db.query(TaskSchedule).count() == 0:
            logger.info("Инициализация стандартных расписаний задач...")

            for schedule_data in DEFAULT_SCHEDULES:
                schedule = TaskSchedule(
                    task_name=schedule_data["task_name"],
                    description=schedule_data["description"],
                    interval_minutes=schedule_data["interval_minutes"],
                    is_active=schedule_data["is_active"],
                    next_run=datetime.now() + timedelta(minutes=schedule_data["interval_minutes"]),
                )
                db.add(schedule)

            db.commit()
            logger.info(f"Добавлено {len(DEFAULT_SCHEDULES)} стандартных расписаний")
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка инициализации расписаний: {e}", exc_info=True)
        raise
