import logging

from fastapi import Request
from sqladmin import ModelView

from app_settings.models import Settings
from database import SessionLocal
from schedule.service import update_start_time_scheduled_task

logger = logging.getLogger(__name__)


class SettingsAdmin(ModelView, model=Settings):
    """Админ-панель для настроек приложения"""

    name = "Настройки приложения"
    name_plural = "Настройки приложения"

    column_list = [
        Settings.start_time,
        Settings.eshmakar_count_of_page_to_parse,
    ]

    form_columns = [
        "start_time",
        "eshmakar_api_token",
        "eshmakar_count_of_page_to_parse",
    ]

    column_labels = {
        "start_time": "Время старта парсеров (например: 1, 2, 13, 14, 21, 22)",
        "eshmakar_api_token": "Токен eshmakar",
        "eshmakar_count_of_page_to_parse": "Количество страниц для парсинга "
        "(бесплатно 1, платно 100)",
    }

    async def on_model_change(self, data, model, is_created, request: Request):
        """Вызывается при создании или изменении задачи"""

        model.start_time = data["start_time"]
        model.eshmakar_api_token = data["eshmakar_api_token"]
        model.eshmakar_count_of_page_to_parse = data["eshmakar_count_of_page_to_parse"]

        db = SessionLocal()

        try:
            if is_created:
                db.add(model)
                db.commit()
                db.refresh(model)
            else:
                # Обновляем существующую запись
                existing_model = db.query(Settings).filter(Settings.id == model.id).first()
                if existing_model:
                    existing_model.start_time = model.start_time
                    existing_model.eshmakar_api_token = model.eshmakar_api_token
                    existing_model.eshmakar_count_of_page_to_parse = (
                        model.eshmakar_count_of_page_to_parse
                    )
                    db.commit()
                    db.refresh(existing_model)

            # Обновляем задачу в планировщике
            update_start_time_scheduled_task(data["start_time"])
        except Exception as e:
            logger.error(f"Ошибка при обработке задачи: {e}")
        finally:
            db.close()
