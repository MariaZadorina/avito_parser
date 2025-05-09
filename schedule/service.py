import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app_settings.models import Settings
from database import SessionLocal
from eshmakar_connector.tasks import enqueue_one_task_for_parsing
from eshmakar_connector.tasks import reset_daily_tasks
from eshmakar_connector.tasks import update_last_task_status_from_eshmakar
from google_sheet.service import fetch_and_process_sheets
from schedule.models import TaskSchedule

# Настройка логгера
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def init_scheduler(db: Session):
    """Инициализация планировщика задач с логированием"""
    try:
        if not scheduler.running:
            scheduler.start()
            logger.info("Планировщик задач успешно запущен")

            try:
                active_tasks = db.query(TaskSchedule).filter_by(is_active=True).all()
                logger.info(f"Найдено {len(active_tasks)} активных задач для планирования")

                for task in active_tasks:
                    add_task_to_scheduler(db, task)
            except Exception as e:
                logger.error(f"Ошибка при загрузке задач: {e}", exc_info=True)
                raise
    except Exception as e:
        logger.critical(f"Ошибка запуска планировщика: {e}", exc_info=True)
        raise
    finally:
        db.close()


def shutdown_scheduler():
    """Остановка планировщика с логированием"""
    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("Планировщик задач успешно остановлен")
    except Exception as e:
        logger.error(f"Ошибка остановки планировщика: {e}", exc_info=True)
        raise


def add_task_to_scheduler(db: Session, task: TaskSchedule):
    """Добавление задачи в планировщик с подробным логированием"""
    try:
        start_time = Settings.get_start_time()
        logger.info(
            f"Добавление задачи '{task.task_name}' с интервалом {task.interval_minutes} минут. "
            f"Следующий запуск: {task.next_run or 'немедленно'}",
        )
        if task.task_name == "reset_daily_tasks":
            scheduler.add_job(
                reset_daily_tasks,
                trigger=CronTrigger(hour=start_time, minute=0),  # Каждый день в 21:00
                args=[task.id],
                id=task.task_name,
                replace_existing=True,
            )
        else:
            scheduler.add_job(
                run_scheduled_task,
                trigger=IntervalTrigger(minutes=task.interval_minutes),
                args=[task.id],
                id=task.task_name,
                next_run_time=task.next_run or datetime.now(),
                replace_existing=True,
            )
        logger.info(f"Задача '{task.task_name}' успешно добавлена в планировщик")
    except Exception as e:
        logger.error(f"Ошибка добавления задачи '{task.task_name}': {e}", exc_info=True)
        raise


def update_start_time_scheduled_task(start_time: int):
    """
    Обновляет или создает задачу в планировщике

    :param start_time: Час запуска (0-23)
    """
    trigger = CronTrigger(hour=start_time, minute=0)

    try:
        # Пытаемся обновить существующую задачу
        scheduler.reschedule_job(
            job_id="reset_daily_tasks",
            trigger=trigger
        )
        print(f"Задача reset_daily_tasks обновлена на {start_time}:00")
    except Exception:
        print(f"Обновить время не удалось")


def run_scheduled_task(task_id: int):
    """Выполнение запланированной задачи с полным трейсингом"""
    db = SessionLocal()
    task = None

    try:
        task = db.query(TaskSchedule).get(task_id)
        if not task:
            logger.error(f"Задача с ID {task_id} не найдена")
            return

        logger.info(f"Начало выполнения задачи: {task.task_name} (ID: {task_id})")

        start_time = datetime.now()
        if task.task_name == "enqueue_one_task_for_parsing":
            enqueue_one_task_for_parsing(db)
        elif task.task_name == "update_last_task_status_from_eshmakar":
            update_last_task_status_from_eshmakar(db)
        elif task.task_name == "fetch_and_process_sheets":
            fetch_and_process_sheets(db)
        elif task.task_name == "reset_daily_tasks":
            reset_daily_tasks(db)
        else:
            logger.warning(f"Неизвестный тип задачи: {task.task_name}")

        task.last_run = datetime.now()
        task.update_next_run()
        db.commit()

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Задача {task.task_name} выполнена успешно. "
            f"Время выполнения: {duration:.2f} секунд",
        )
    except Exception as e:
        db.rollback()
        task_name = task.task_name if task else f"ID:{task_id}"
        logger.error(
            f"Ошибка выполнения задачи {task_name}: {e}",
            exc_info=True,
        )
    finally:
        db.close()
