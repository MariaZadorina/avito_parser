import logging

from sqladmin import ModelView

from eshmakar_connector.models import Task


# Настройка логирования
logger = logging.getLogger(__name__)


class TaskAdmin(ModelView, model=Task):
    """Админ-панель для управления задачами парсинга"""

    name = "Задача"
    name_plural = "Задачи на парсинг для eshmakar"

    # Отображаемые колонки в списке задач
    column_list = [
        Task.status,
        # Task.comment,
        Task.link_to_google_sheet,
        Task.in_eshmakar_queue,
        Task.has_data_in_db,
        Task.link_to_parse,
    ]
    column_labels = {
        "external_id": "Идентификатор системы eshmakar",
        "link_to_parse": "Ссылка на парсинг данных с авито",
        "created_date": "Дата создания",
        "parsed_date": "Дата парсинга",
        "link_to_google_sheet": "Ссылка на гугл таблицу",
        "status": "Статус",
        "title": "Заголовок",
        "has_data_in_db": "Данные в нашей бд",
        "in_eshmakar_queue": "В очереди eshmakar",
        # "comment": "Комментарий",
    }

    # Колонки для формы редактирования
    form_columns = [Task.link_to_parse]
