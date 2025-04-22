import csv
import hashlib
import logging
import re
from datetime import datetime
from io import StringIO

import requests
from sqlalchemy.orm import Session

from eshmakar_connector.models import Task
from eshmakar_connector.models import TaskStatus
from google_sheet.models import GoogleSheetRecord

# Настройка логирования
logger = logging.getLogger(__name__)


def fetch_and_process_sheets(db: Session, batch_size: int = 10) -> dict[str, int]:
    """
    Обрабатывает Google Sheets из Task, которые еще не были загружены в БД
    или требуют обновления.

    Args:
        db: Сессия базы данных SQLAlchemy
        batch_size: Максимальное количество задач для обработки за один вызов

    Returns:
        Словарь с результатами обработки в формате {sheet_url: new_records_count}
    """
    results = {}
    logger.info(f"Начало обработки Google Sheets (batch_size={batch_size})")

    try:
        tasks = (
            db.query(Task)
            .filter(
                Task.has_data_in_db.is_(False),
                Task.link_to_google_sheet.isnot(None),  # Проверка на None
                Task.link_to_google_sheet != "",  # Проверка на пустую строку
            )
            .limit(batch_size)
            .all()
        )
        logger.info(f"Найдено {len(tasks)} задач для обработки")

        for task in tasks:
            sheet_url = task.link_to_google_sheet
            logger.debug(f"Обработка задачи ID={task.id}, URL={sheet_url}")

            try:
                sheet_id = extract_sheet_id(sheet_url)
                logger.debug(f"Извлечен Sheet ID: {sheet_id}")

                csv_data = fetch_sheet_data(sheet_id)
                logger.debug(f"Получено {len(csv_data)} байт CSV данных")

                new_records = process_sheet_data(csv_data, sheet_id, task.id, db)
                logger.info(f"Добавлено {new_records} новых записей из таблицы {sheet_url}")

                task.has_data_in_db = True if new_records > 0 else task.has_data_in_db
                results[sheet_url] = new_records

            except requests.RequestException as e:
                logger.error(f"Ошибка при загрузке таблицы {sheet_url}: {str(e)}")
                task.status = TaskStatus.ERROR
                task.parsed_date = datetime.utcnow()
            except Exception as e:
                logger.error(
                    f"Неожиданная ошибка при обработке таблицы {sheet_url}: {str(e)}",
                    exc_info=True,
                )
                task.status = TaskStatus.ERROR
                task.parsed_date = datetime.utcnow()

        db.commit()
        logger.info(f"Успешно обработано {len(results)} таблиц")
        return results

    except Exception as e:
        db.rollback()
        logger.error(f"Критическая ошибка при обработке Google Sheets: {str(e)}", exc_info=True)
        raise


def fetch_sheet_data(sheet_id: str) -> str:
    """
    Загружает данные публичной Google Sheets в формате CSV

    Args:
        sheet_id: ID Google таблицы

    Returns:
        Строка с CSV данными

    Raises:
        requests.RequestException: При ошибках HTTP запроса
        ValueError: При проблемах с декодированием данных
    """
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    logger.debug(f"Запрос данных таблицы {sheet_id}")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content.decode("utf-8")
    except requests.RequestException as e:
        logger.error(f"Ошибка при запросе таблицы {sheet_id}: {str(e)}")
        raise
    except UnicodeDecodeError as e:
        logger.error(f"Ошибка декодирования данных таблицы {sheet_id}: {str(e)}")
        raise ValueError(f"Не удалось декодировать данные таблицы {sheet_id}")


def process_sheet_data(csv_data: str, sheet_id: str, task_id: int, db: Session) -> int:
    """
    Обрабатывает CSV данные и сохраняет новые записи в БД

    Args:
        csv_data: Строка с CSV данными
        sheet_id: ID Google таблицы
        task_id: ID исходной задачи
        db: Сессия базы данных

    Returns:
        Количество добавленных новых записей
    """
    new_records = 0
    logger.debug(f"Начало обработки CSV данных для таблицы {sheet_id}")

    try:
        reader = csv.DictReader(StringIO(csv_data))
        for row_num, row in enumerate(reader, 1):
            try:
                row_hash = hashlib.md5(str(row).encode()).hexdigest()
                exists = (
                    db.query(GoogleSheetRecord)
                    .filter_by(
                        sheet_id=sheet_id,
                        row_hash=row_hash,
                    )
                    .first()
                )

                if not exists:
                    record = GoogleSheetRecord(
                        sheet_id=sheet_id,
                        source_task_id=task_id,
                        row_data=row,
                        row_hash=row_hash,
                        is_exported=False,
                    )
                    db.add(record)
                    new_records += 1
                    logger.debug(f"Добавлена новая запись (строка {row_num})")

            except Exception as e:
                logger.error(f"Ошибка обработки строки {row_num}: {str(e)}", exc_info=True)
                continue

        logger.info(f"Обработано {row_num} строк, добавлено {new_records} новых записей")
        return new_records

    except csv.Error as e:
        logger.error(f"Ошибка парсинга CSV данных: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка при обработке CSV: {str(e)}", exc_info=True)
        raise


def extract_sheet_id(url: str) -> str:
    """
    Надежно извлекает ID таблицы из URL Google Sheets

    Args:
        url: URL Google таблицы

    Returns:
        ID таблицы

    Raises:
        ValueError: Если не удалось извлечь ID
    """
    logger.debug(f"Попытка извлечь ID из URL: {url}")

    patterns = [
        r"/spreadsheets/d/([a-zA-Z0-9-_]+)",  # Стандартный формат
        r"/d/([a-zA-Z0-9-_]+)/",  # URL с /edit?usp=sharing
        r"/d/e/([a-zA-Z0-9-_]+)/",  # URL с /pubhtml
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            sheet_id = match.group(1)
            logger.debug(f"ID {sheet_id} извлечен с помощью pattern: {pattern}")
            return sheet_id

    logger.error(f"Не удалось извлечь ID таблицы из URL: {url}")
    raise ValueError(f"Неверный формат URL Google Sheets: {url}")
