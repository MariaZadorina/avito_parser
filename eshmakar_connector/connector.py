import json
import logging
from datetime import datetime
from typing import Any

import requests

from app_settings.models import Settings

logger = logging.getLogger(__name__)

# Конфигурация API
BASE_URL = "https://eshmakar.ru/API/V1"
PARSE_AD_URL = f"{BASE_URL}/ads/parseAd"
ADD_TASK_URL = f"{BASE_URL}/tasks/add"
TASKS_URL = f"{BASE_URL}/tasks/all"
LAST_TASK_URL = f"{BASE_URL}/tasks/last"


class EshmakarAPIError(Exception):
    """Базовый класс для ошибок API"""

    pass


def get_headers():
    return {
        "Token": Settings.get_eshmakar_api_token(),
        "Content-Type": "application/json",
    }


def _handle_response(response: requests.Response) -> dict[str, Any] | None:
    """Обработка ответа от API"""
    try:
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        error_msg = f"HTTP error occurred: {http_err}"
        if response.status_code == 400:
            error_msg = "Bad Request: Неверный запрос"
        elif response.status_code == 401:
            error_msg = "Unauthorized: Неверный токен"
        elif response.status_code == 404:
            error_msg = "Not Found: Ничего не найдено"
        logger.error(error_msg)
        raise EshmakarAPIError(error_msg)
    except json.JSONDecodeError as json_err:
        error_msg = f"JSON decode error: {json_err}"
        logger.error(error_msg)
        raise EshmakarAPIError(error_msg)
    except Exception as err:
        error_msg = f"Unexpected error: {err}"
        logger.error(error_msg)
        raise EshmakarAPIError(error_msg)


def _save_to_json(data: dict[str, Any], prefix: str = "response") -> str:
    """Сохранение данных в JSON файл"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.json"

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"Данные сохранены в файл: {filename}")
        return filename
    except OSError as e:
        logger.error(f"Ошибка при сохранении файла {filename}: {e}")
        raise


def parse_ad(link_to_parse: str) -> dict[str, Any]:
    """
    Парсинг объявления по ссылке или ID

    Args:
        link_to_parse: Ссылка на объявление или его ID

    Returns:
        Словарь с данными объявления

    Raises:
        EshmakarAPIError: Если произошла ошибка при запросе
    """
    logger.info(f"Начало парсинга объявления: {link_to_parse}")

    data = {"linkToParse": link_to_parse}

    try:
        response = requests.post(PARSE_AD_URL, headers=get_headers(), json=data)
        result = _handle_response(response)
        _save_to_json(result, "ad_response")
        logger.info("Парсинг объявления выполнен успешно")
        return result
    except Exception as e:
        logger.error(f"Ошибка при парсинге объявления: {e}")
        raise


def add_task_to_parse(
    link: str,
    count_of_page_to_parse: int = Settings.get_count_of_page_to_parse(),
    send_report_to_email: bool = False,
    remove_duplicates: bool = True,
    seller_params: bool = False,
    is_scheduled: bool = False,
) -> str:
    """
    Добавление задачи на парсинг

    Args:
        link: Ссылка для парсинга
        count_of_page_to_parse: Количество страниц для парсинга
        send_report_to_email: Отправлять отчет на email
        remove_duplicates: Удалять дубликаты
        seller_params: Парсить параметры продавца
        is_scheduled: Планируемая задача

    Returns:
        Ответ сервера в виде строки

    Raises:
        EshmakarAPIError: Если произошла ошибка при запросе
    """
    logger.info(f"Добавление задачи на парсинг: {link}")

    data = {
        "link": link,
        "countOfPageToParse": count_of_page_to_parse,
        "sendReportToEmail": send_report_to_email,
        "removeDuplicates": remove_duplicates,
        "sellerParams": seller_params,
        "isScheduled": is_scheduled,
    }

    try:
        response = requests.post(ADD_TASK_URL, headers=get_headers(), json=data)
        # Проверка кода состояния ответа
        if response.status_code == 200:
            logger.info(f"Успешно 200: {response.text}")
        elif response.status_code == 400:
            logger.error("Ошибка 400: Неверный запрос")
        elif response.status_code == 401:
            logger.error("Ошибка 401: Неверный токен")
        else:
            logger.error(f"Ошибка {response.status_code}: {response.text}")
        return response.text
    except Exception as e:
        logger.error(f"Ошибка при добавлении задачи: {e}")
        raise


def fetch_tasks() -> list[dict[str, Any]]:
    """
    Получение списка всех задач

    Returns:
        Список задач

    Raises:
        EshmakarAPIError: Если произошла ошибка при запросе
    """
    logger.info("Запрос списка задач")

    try:
        response = requests.get(TASKS_URL, headers=get_headers())
        tasks = _handle_response(response)
        _save_to_json(tasks, "tasks")
        logger.info(f"Получено {len(tasks)} задач")
        return tasks
    except Exception as e:
        logger.error(f"Ошибка при получении задач: {e}")
        raise


def fetch_last_task() -> dict[str, Any]:
    """
    Получение последней задачи

    Returns:
        Задача

    Raises:
        EshmakarAPIError: Если произошла ошибка при запросе
    """
    logger.info("Запрос последней задачи")

    try:
        response = requests.get(LAST_TASK_URL, headers=get_headers())
        task = _handle_response(response)
        _save_to_json(task, "last_task")
        print(task)
        return task
    except Exception as e:
        logger.error(f"Ошибка при получении последней задачи: {e}")
        raise


# Пример использования
if __name__ == "__main__":
    try:
        # Пример парсинга объявления
        ad_data = parse_ad("3274612429")
        logger.debug(f"Данные объявления: {ad_data}")

        # Пример добавления задачи
        task_result = add_task_to_parse(
            link="https://www.avito.ru/moskva_i_mo/kvartiry/sdam/na_dlitelnyy_srok-ASgBAgICAkSSA8gQ8AeQUg?cd=1",
            count_of_page_to_parse=1,
        )
        logger.info(task_result)

        # Пример получения задач
        tasks = fetch_tasks()
        logger.info(f"Получено задач: {len(tasks)}")

    except EshmakarAPIError as e:
        logger.error(f"Ошибка в работе с API: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")


# URL: https: // eshmakar.ru / API / V1 / ads / parseAd
# Метод: POST
# Формат данных: application / json
#
# Заголовки: Token: Ваш API - токен
#
# Тело запроса:
# {
#     "linkToParse": "https://www.avito.ru/kirovskaya_oblast_kirov/telefony/mobilnye_telefony/honor-ASgBAgICAkS0wA3u_juwwQ2I_Dc?cd=1&p=2" # noqa E501
# }
#
# или же, вместо ссылки можете просто указать id номер объявления, вот так:
# {
#     "linkToParse": "3274612429"
# }
#
# Коды состояния ответа:
# - 200 OK
# - 400 BadRequest: Неверный запрос
# - 401 Unauthorized: Неверный токен
# - 404 NotFound: Ничего не найдено


# URL: https: // eshmakar.ru / API / V1 / tasks / add
# Метод: POST
# Формат данных: application / json
#
# Заголовки:
# Token: Ваш API - токен
#
# Тело запроса:
# {
#     "link": "https://www.avito.ru/moskva_i_mo/kvartiry/sdam/na_dlitelnyy_srok-ASgBAgICAkSSA8gQ8AeQUg?cd=1&f=ASgBAQICAkSSA8gQ8AeQUgFAzAgkkFmOWQ", # noqa E501
#     "countOfPageToParse": 1,
#     "sendReportToEmail": false,
#     "removeDuplicates": true,
#     "sellerParams": false,
#     "isScheduled": false
# }
#
# Коды состояния ответа:
# - 200 OK: Задача успешно добавлена!
# - 400 Bad Request: Неверный запрос
# - 401 Unauthorized: Неверный токен


# URL: https://eshmakar.ru/API/V1/tasks/all
# Метод: GET
# Формат данных: application / json
#
# Заголовки: Token: Ваш API - токен
#
# Коды состояния ответа: \
# - 200 OK
# - 400 BadRequest: Неверный запрос
# - 401 Unauthorized: Неверный токен
# - 404 Not Found: Ничего не найдено
#
# Пример ответа:
# {
#     {
#         "id": 9,
#         "taskNumber": 12131,
#         "linkToParse": "https://www.avito.ru/kazan/kvartiry/sdam/na_dlitelnyy_srok/1-komnatnye-ASgBAgICA0SSA8gQ8AeQUswIjlk?cd=1&context=H4sIAAAAAAAA_wFCAL3_YToxOntzOjU6Inhfc2d0IjtzOjQwOiIwZmM5M2Y2ZGFmMGIxNWYwYTEzZjlmYjVjOTYzNjk1M2MyYzdkM2Q3Ijt9MFr6_UIAAAA&radius=0&presentationType=serp", # noqa E501
#         "createdDate": 1688050495000,
#         "parsedDate": 1688050602000,
#         "linkToGoogleSheet": "https://docs.google.com/spreadsheets/d/1S3JQVdYcauIgXB6hlzj0Yl6ZVguIo2-TImfMK1PSjeA/edit", # noqa E501
#         "status": "ВЫПОЛНЕНО",
#         "user": "user695651",
#         "numberInQueue": null,
#         "countOfPagesToParse": 5,
#         "title": "Авито | Недвижимость | Квартиры | Снять | На длительный срок | 1-комнатные | Казань | 2023-06-29 17:54:55", # noqa E501
#         "sendLinkToEmail": false,
#         "removeDuplicates": false,
#         "parsePhoneNumbers": true,
#         "sellerParams": false,
#         "timeToParse": null
#     },
#     {
#         "id": 10,
#         "taskNumber": 12132,
#         "linkToParse": "https://www.avito.ru/naberezhnye_chelny/kvartiry/sdam/na_dlitelnyy_srok/1-komnatnye-ASgBAgICA0SSA8gQ8AeQUswIjlk?cd=1", # noqa E501
#         "createdDate": 1688056538000,
#         "parsedDate": 1688056639000,
#         "linkToGoogleSheet": "https://docs.google.com/spreadsheets/d/12DqhqytVfHuWP2-uNcghNVRdeqf1sMeXZTE4KaAjmK8/edit", # noqa E501
#         "status": "ВЫПОЛНЕНО",
#         "user": "user695651",
#         "numberInQueue": null,
#         "countOfPagesToParse": 5,
#         "title": "Авито | Недвижимость | Квартиры | Снять | На длительный срок | 1-комнатные | Набережные Челны | 2023-06-29 19:35:38", # noqa E501
#         "sendLinkToEmail": false,
#         "removeDuplicates": false,
#         "parsePhoneNumbers": true,
#         "sellerParams": false,
#         "timeToParse": null
#     }
# }
