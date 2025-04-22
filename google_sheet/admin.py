from sqladmin import ModelView

from google_sheet.models import GoogleSheetRecord


class GoogleSheetRecordAdmin(ModelView, model=GoogleSheetRecord):
    name = "Данные из гугл таблицы"
    name_plural = "Данные из гугл таблиц"

    column_list = [
        GoogleSheetRecord.sheet_id,
        GoogleSheetRecord.is_exported,
        GoogleSheetRecord.created_at,
    ]

    column_labels = {
        "sheet_id": "Идентификатор google таблицы",
        "row_data": "Данные одной строки из google таблицы",
        "row_hash": "Хэш строки",
        "is_exported": "Данные экспортированы в базу",
        "created_at": "Дата создания",
        "updated_at": "Дата обновления",
    }
