from sqladmin import ModelView

from google_sheet.models import GoogleSheetRecord


class GoogleSheetRecordAdmin(ModelView, model=GoogleSheetRecord):
    name = "Данные из гугл таблицы"
    name_plural = "Данные из гугл таблиц"

    column_list = [
        GoogleSheetRecord.sheet_id,
        GoogleSheetRecord.created_at,
    ]

    column_labels = {
        "sheet_id": "Идентификатор google таблицы",
        "row_data": "Данные одной строки из google таблицы",
        "row_hash": "Хэш строки",
        "created_at": "Дата создания",
        "updated_at": "Дата обновления",
    }
