import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqladmin import Admin

from app_settings.admin import SettingsAdmin
from app_settings.init_settings import init_settings
from database import Base
from database import engine
from database import SessionLocal
from eshmakar_connector.admin import TaskAdmin
from google_sheet.admin import GoogleSheetRecordAdmin
from google_sheet.routers import sheets_router
from schedule.admin import TaskScheduleAdmin
from schedule.initial_data import init_default_schedules
from schedule.routers import schedule_router
from schedule.service import init_scheduler
from schedule.service import shutdown_scheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("avito_parser.log"),
    ],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создание всех таблиц в базе данных
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        init_settings(db)
        init_default_schedules(db)
        init_scheduler(db)

        yield
    finally:
        db.close()
        shutdown_scheduler()


app = FastAPI(lifespan=lifespan)

app.include_router(sheets_router, prefix="/api")
app.include_router(schedule_router)


# Инициализация админ-панели
admin = Admin(
    app,
    engine,
    title="My Admin Panel",
    base_url="/admin",
)

# Явно указываем базовый URL

# Регистрация модели в админ-панели
admin.add_view(TaskAdmin)
admin.add_view(GoogleSheetRecordAdmin)
admin.add_view(TaskScheduleAdmin)
admin.add_view(SettingsAdmin)


# Для запуска приложения через uvicorn
if __name__ == "__main__":
    logger.info("Start app")
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
