import logging
import os

from app_settings.models import Settings

logger = logging.getLogger(__name__)


def init_settings(db):
    """Инициализирует настройки при старте приложения"""
    try:
        settings = db.query(Settings).first()

        if not settings:
            new_settings = Settings(
                start_time=int(os.getenv("START_TIME", 21)),
                eshmakar_api_token=os.getenv("ESHMAKAR_API_TOKEN", ""),
                eshmakar_count_of_page_to_parse=os.getenv("ESHMAKAR_COUNT_OF_PAGE_TO_PARSE", 1),
            )
            db.add(new_settings)
            db.commit()
    except Exception as e:
        logger.error(f"Error initializing settings: {e}")
