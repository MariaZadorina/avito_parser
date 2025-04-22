import logging
from datetime import datetime
from datetime import timedelta

from fastapi import Request
from fastapi.responses import JSONResponse
from sqladmin import action
from sqladmin import ModelView

from database import SessionLocal
from schedule.models import TaskSchedule
from schedule.service import add_task_to_scheduler
from schedule.service import run_scheduled_task
from schedule.service import scheduler

logger = logging.getLogger(__name__)


class TaskScheduleAdmin(ModelView, model=TaskSchedule):
    """Админ-панель для управления планировщиком задач"""

    name = "Планировщик задач"
    name_plural = "Планировщики задач"

    column_list = [
        TaskSchedule.task_name,
        TaskSchedule.description,
        TaskSchedule.interval_minutes,
        TaskSchedule.is_active,
        TaskSchedule.last_run,
        TaskSchedule.next_run,
    ]

    form_columns = [
        "task_name",
        "description",
        "interval_minutes",
        "is_active",
    ]

    column_labels = {
        "task_name": "Название задачи (не заполнять самостоятельно)",
        "description": "Описание задачи",
        "interval_minutes": "Периодичность запуска в минутах",
        "is_active": "Задача активна?",
        "last_run": "Время последнего запуска",
        "next_run": "Время следующего запуска",
    }

    async def on_model_change(self, data, model, is_created, request: Request):
        """Вызывается при создании или изменении задачи"""

        model.task_name = data["task_name"]
        model.description = data["description"]
        model.interval_minutes = data["interval_minutes"]
        model.is_active = data["is_active"]
        model.update_next_run()

        db = SessionLocal()

        try:
            if is_created:
                db.add(model)
                db.commit()
                db.refresh(model)
            else:
                # Обновляем существующую запись
                existing_model = db.query(TaskSchedule).filter(TaskSchedule.id == model.id).first()
                if existing_model:
                    existing_model.task_name = model.task_name
                    existing_model.description = model.description
                    existing_model.interval_minutes = model.interval_minutes
                    existing_model.is_active = model.is_active
                    existing_model.update_next_run()
                    db.commit()
                    db.refresh(existing_model)
                    model = existing_model  # Обновляем ссылку на модель

            # Обновляем задачу в планировщике
            add_task_to_scheduler(db, model)
        except Exception as e:
            logger.error(f"Ошибка при обработке задачи: {e}")
        finally:
            db.close()

    async def on_model_delete(self, model: TaskSchedule, request: Request):
        """Вызывается при удалении задачи"""
        scheduler.remove_job(model.task_name)
        logger.info(f"Задача '{model.task_name}' удалена из планировщика")

    @action(
        name="run_tasks",
        label="Запустить задачи",
        confirmation_message="Вы уверены, что хотите запустить выбранные задачи?",
    )
    def run_tasks(self, request: Request):
        """Действие для ручного запуска выбранных задач"""
        try:
            # Получаем ID выбранных задач
            ids = request.query_params.getlist("pks")
            int_ids = [int(id) for id in ids]
            logger.info(f"Запуск задач по ручному запросу. IDs: {int_ids}")

            results = []
            db = SessionLocal()

            try:
                tasks = db.query(TaskSchedule).filter(TaskSchedule.id.in_(int_ids)).all()
                logger.info(f"Найдено {len(tasks)} задач для запуска")

                for task_schedule in tasks:
                    task_name = task_schedule.task_name
                    logger.info(f"Обработка задачи: {task_name} (ID: {task_schedule.id})")

                    try:
                        # Выполняем задачу
                        run_scheduled_task(task_schedule.id)
                        logger.debug(f"Задача {task_name} выполнена успешно")

                        # Обновляем время выполнения
                        task_schedule.last_run = datetime.utcnow()
                        task_schedule.next_run = datetime.utcnow() + timedelta(
                            minutes=task_schedule.interval_minutes,
                        )
                        db.commit()
                        logger.debug(f"Временные метки задачи {task_name} обновлены")

                        results.append(f"Задача {task_name} запущена успешно")

                    except Exception as task_error:
                        db.rollback()
                        error_msg = f"Ошибка при выполнении задачи {task_name}: {str(task_error)}"
                        logger.error(error_msg, exc_info=True)
                        results.append(error_msg)

                return JSONResponse(
                    content={
                        "result": "OK",
                        "details": results,
                    },
                    status_code=200,
                )

            except Exception as db_error:
                db.rollback()
                error_msg = f"Ошибка при работе с базой данных: {str(db_error)}"
                logger.critical(error_msg, exc_info=True)
                return JSONResponse(
                    content={"result": "ERROR", "error": error_msg},
                    status_code=500,
                )

            finally:
                db.close()

        except Exception as e:
            error_msg = f"Неожиданная ошибка при обработке запроса: {str(e)}"
            logger.critical(error_msg, exc_info=True)
            return JSONResponse(
                content={"result": "ERROR", "error": error_msg},
                status_code=500,
            )
