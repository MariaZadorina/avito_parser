import logging
from datetime import datetime
from datetime import time
from urllib.parse import parse_qs
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from database import SessionLocal
from eshmakar_connector.connector import add_task_to_parse
from eshmakar_connector.connector import fetch_last_task
from eshmakar_connector.connector import fetch_tasks
from eshmakar_connector.models import Task
from eshmakar_connector.models import TaskStatus
from settings import END_TIME
from settings import START_TIME

# Загружаем переменные окружения из файла .env


# Настройка логирования
logger = logging.getLogger(__name__)


def is_time_window_active() -> bool:
    """Проверяет, что сейчас 21:00–03:00."""
    now = datetime.now().time()
    return time(START_TIME, 0) <= now or now <= time(END_TIME, 0)


def reset_daily_tasks(db: Session):
    """Сброс статусов задач в START_TIME каждый день."""
    db_session = SessionLocal()
    if not is_time_window_active():  # Проверяем 21:00–03:00
        return
    try:
        db_session.query(Task).filter(
            Task.status != TaskStatus.ERROR,
        ).update(
            {
                "status": TaskStatus.IN_PROGRESS,
                "link_to_google_sheet": None,
                "has_data_in_db": False,
                "in_eshmakar_queue": False,
                "parsed_date": None,
            },
        )
        logger.info("Ежедневный сброс задач выполнен успешно")
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        logger.error(f"Ошибка сброса задач: {str(e)}")
        raise
    finally:
        db_session.close()


def enqueue_one_task_for_parsing(db_session: Session):
    """Постановка одной задачи в очередь на парсинг в eshmakar, только если:
    1. Нет активных задач без ссылки на Google таблицу
    2. В очереди нет других задач

    Args:
        db_session: Сессия базы данных SQLAlchemy
    """
    if not is_time_window_active():  # Проверяем 21:00–03:00
        return
    # Проверяем, есть ли задачи без ссылки на Google таблицу
    tasks_without_sheet = (
        db_session.query(Task)
        .filter(
            Task.status == TaskStatus.IN_PROGRESS,
            Task.link_to_google_sheet.is_(None),
            Task.in_eshmakar_queue.is_(True),
        )
        .count()
    )

    if tasks_without_sheet > 0:
        logger.info(
            f"Найдено {tasks_without_sheet} задач без ссылки на Google таблицу - "
            f"новая задача не будет добавлена",
        )
        return

    # Ищем первую задачу, которую можно поставить в очередь
    task_to_enqueue = (
        db_session.query(Task)
        .filter(
            Task.status == TaskStatus.IN_PROGRESS,
            Task.in_eshmakar_queue.is_(False),
            Task.link_to_google_sheet.is_(None),  # На всякий случай проверяем еще раз
        )
        .first()
    )

    if not task_to_enqueue:
        logger.info("Нет подходящих задач для постановки в очередь")
        return

    try:
        logger.info(f"Попытка постановки задачи {task_to_enqueue.id} в очередь")
        result = add_task_to_parse(link=task_to_enqueue.link_to_parse)

        if result == "Задача успешно добавлена!":
            task_to_enqueue.in_eshmakar_queue = True
            db_session.commit()
            logger.info(
                f"Задача {task_to_enqueue.id} успешно поставлена в очередь eshmakar",
            )
        else:
            logger.error(f"Ошибка при постановке задачи {task_to_enqueue.id} в очередь: {result}")
    except Exception as e:
        db_session.rollback()
        logger.error(
            f"Ошибка при добавлении задачи {task_to_enqueue.id} в очередь: {str(e)}",
            exc_info=True,
        )


def update_last_task_status_from_eshmakar(db_session: Session):
    """Обновление cтатуса последней задачи на основе данных из eshmakar API

    Args:
        db_session: Сессия базы данных SQLAlchemy
    """
    if not is_time_window_active():  # Проверяем 21:00–03:00
        return

    # Ищем единстенную задачу которая в очереди у eshmakar но у неё нет ссылки на гугл таблицу
    task = (
        db_session.query(Task)
        .filter(
            Task.status == TaskStatus.IN_PROGRESS,
            Task.in_eshmakar_queue.is_(True),
            Task.link_to_google_sheet.is_(None),
        )
        .first()
    )

    if not task:
        logger.info("Нет задач для обновления статуса")
        return

    logger.info(f"Найдена {task.id} задача для обновления статуса")

    try:
        eshmakar_task = fetch_last_task()
        logger.info(f"Получена {eshmakar_task} задача из eshmakar API")
    except Exception as e:
        logger.error(f"Ошибка при получении задачи из eshmakar API: {str(e)}")
        return

    try:
        # Обновляем поля задачи
        if "id" in eshmakar_task:
            task.external_id = eshmakar_task["id"]

        if "parsedDate" in eshmakar_task and eshmakar_task["parsedDate"]:
            task.parsed_date = datetime.fromtimestamp(
                eshmakar_task["parsedDate"] / 1000,
            )

        if "linkToGoogleSheet" in eshmakar_task:
            task.link_to_google_sheet = eshmakar_task["linkToGoogleSheet"]

        if "status" in eshmakar_task:
            try:
                task.status = TaskStatus(eshmakar_task["status"])
            except ValueError:
                logger.warning(
                    f"Неизвестный статус задачи {task.id}: " f"{eshmakar_task['status']}",
                )

        if "title" in eshmakar_task:
            task.title = eshmakar_task["title"]

        logger.debug(f"Задача {task.id} успешно обновлена")
    except Exception as e:
        logger.error(
            f"Ошибка при обновлении задачи {task.id}: {str(e)}",
            exc_info=True,
        )

    logger.info(f"Обновлена {task.id} задача")


def enqueue_tasks_for_parsing(db_session: Session):
    """Постановка задач в очередь на парсинг в eshmakar

    Args:
        db_session: Сессия базы данных SQLAlchemy
    """
    pending_tasks = (
        db_session.query(Task)
        .filter(
            Task.status == TaskStatus.IN_PROGRESS,
            Task.in_eshmakar_queue.is_(False),
        )
        .all()
    )

    logger.info(f"Найдено {len(pending_tasks)} задач для постановки в очередь")

    for task in pending_tasks:
        try:
            result = add_task_to_parse(link=task.link_to_parse)
            if result == "Задача успешно добавлена!":
                task.in_eshmakar_queue = True
                logger.debug(f"Задача {task.id} поставлена в очередь eshmakar")
            else:
                logger.error(f"Задача {task.id} НЕ поставлена в очередь eshmakar {result=}")
        except Exception as e:
            logger.error(f"Ошибка при добавлении задачи {task.id} в очередь: {str(e)}")


# def are_urls_equivalent(url1: str, url2: str) -> bool:
#     """Проверяет эквивалентность двух URL, игнорируя параметры запроса
#
#     Args:
#         url1: Первый URL для сравнения
#         url2: Второй URL для сравнения
#
#     Returns:
#         bool: True если URL эквивалентны (схема, хост и путь совпадают)
#     """
#     parsed_url1 = urlparse(url1)
#     parsed_url2 = urlparse(url2)
#
#     return (parsed_url1.scheme == parsed_url2.scheme and
#             parsed_url1.netloc == parsed_url2.netloc and
#             parsed_url1.path == parsed_url2.path)


def are_urls_equivalent(url1: str, url2: str) -> bool:
    """
    Проверяет эквивалентность двух URL, включая параметры запроса

    Args:
        url1: Первый URL для сравнения
        url2: Второй URL для сравнения

    Returns:
        bool: True если URL полностью эквивалентны (схема, хост, путь и параметры)
    """
    parsed1 = urlparse(url1)
    parsed2 = urlparse(url2)

    # Сравниваем базовые компоненты URL
    if (
        parsed1.scheme != parsed2.scheme
        or parsed1.netloc != parsed2.netloc
        or parsed1.path != parsed2.path
    ):
        return False

    # Парсим параметры запроса
    params1 = parse_qs(parsed1.query)
    params2 = parse_qs(parsed2.query)

    # Сравниваем параметры
    return params1 == params2


def update_tasks_status_from_eshmakar(db_session: Session):
    """Обновление статусов задач на основе данных из eshmakar API

    Args:
        db_session: Сессия базы данных SQLAlchemy
    """
    pending_tasks = (
        db_session.query(Task)
        .filter(
            Task.status == TaskStatus.IN_PROGRESS,
        )
        .all()
    )

    if not pending_tasks:
        logger.info("Нет задач для обновления статуса")
        return

    logger.info(f"Найдено {len(pending_tasks)} задач для обновления статуса")

    try:
        eshmakar_tasks = fetch_tasks()
        eshmakar_tasks_map = {task["linkToParse"]: task for task in eshmakar_tasks}

        logger.info(f"Получено {len(eshmakar_tasks)} задач из eshmakar API")
    except Exception as e:
        logger.error(f"Ошибка при получении задач из eshmakar API: {str(e)}")
        return

    updated_count = 0

    for task in pending_tasks:
        try:
            # Ищем соответствующую задачу в ответе API
            matching_eshmakar_task = None

            for eshmakar_url, eshmakar_task in eshmakar_tasks_map.items():
                if are_urls_equivalent(task.link_to_parse, eshmakar_url):
                    matching_eshmakar_task = eshmakar_task
                    break

            if not matching_eshmakar_task:
                logger.debug(f"Для задачи {task.id} не найдено соответствие в eshmakar")
                continue

            # Обновляем поля задачи
            if "id" in matching_eshmakar_task:
                task.external_id = matching_eshmakar_task["id"]

            if "parsedDate" in matching_eshmakar_task and matching_eshmakar_task["parsedDate"]:
                task.parsed_date = datetime.fromtimestamp(
                    matching_eshmakar_task["parsedDate"] / 1000,
                )

            if "linkToGoogleSheet" in matching_eshmakar_task:
                task.link_to_google_sheet = matching_eshmakar_task["linkToGoogleSheet"]

            if "status" in matching_eshmakar_task:
                try:
                    task.status = TaskStatus(matching_eshmakar_task["status"])
                except ValueError:
                    logger.warning(
                        f"Неизвестный статус задачи {task.id}: "
                        f"{matching_eshmakar_task['status']}",
                    )

            if "title" in matching_eshmakar_task:
                task.title = matching_eshmakar_task["title"]

            updated_count += 1
            logger.debug(f"Задача {task.id} успешно обновлена")

        except Exception as e:
            logger.error(
                f"Ошибка при обновлении задачи {task.id}: {str(e)}",
                exc_info=True,
            )

    logger.info(f"Обновлено {updated_count} из {len(pending_tasks)} задач")
