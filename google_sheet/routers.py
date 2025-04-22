from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from sqlalchemy import distinct
from sqlalchemy import func
from sqlalchemy import Integer

from database import SessionLocal
from google_sheet.models import GoogleSheetRecord

sheets_router = APIRouter()


@sheets_router.get("/sheets/stats")
async def get_sheets_stats():
    """
    Возвращает статистику по всем Google Sheets:
    - Общее количество уникальных таблиц
    - Общее количество записей
    - Количество неэкспортированных записей
    - Детали по каждой таблице
    """
    db = SessionLocal()
    # Общая статистика
    total_stats = db.query(
        func.count(distinct(GoogleSheetRecord.sheet_id)).label("total_sheets"),
        func.count(GoogleSheetRecord.id).label("total_records"),
        func.sum(func.cast(GoogleSheetRecord.is_exported is False, Integer)).label(
            "unexported_records",
        ),
    ).first()

    # Статистика по каждой таблице
    sheets_stats = (
        db.query(
            GoogleSheetRecord.sheet_id,
            func.count(GoogleSheetRecord.id).label("total_records"),
            func.sum(func.cast(GoogleSheetRecord.is_exported is False, Integer)).label(
                "unexported_records",
            ),
        )
        .group_by(GoogleSheetRecord.sheet_id)
        .all()
    )

    return {
        "total_sheets": total_stats.total_sheets,
        "total_records": total_stats.total_records,
        "unexported_records": total_stats.unexported_records or 0,
        "sheets": [
            {
                "sheet_id": stat.sheet_id,
                "total_records": stat.total_records,
                "unexported_records": stat.unexported_records or 0,
            }
            for stat in sheets_stats
        ],
    }


@sheets_router.get("/sheets/{sheet_id}/export")
async def export_data(
    sheet_id: str,
    batch_size: int = Query(5, gt=0, le=50),
):
    """
    Экспорт данных из конкретной Google Sheets
    Возвращает:
    - Количество выгруженных записей
    - Сами данные
    - Ссылку на следующую партию
    - Статистику по оставшимся записям
    """
    db = SessionLocal()
    # Получаем записи для экспорта
    records = (
        db.query(GoogleSheetRecord)
        .filter_by(
            sheet_id=sheet_id,
            is_exported=False,
        )
        .limit(batch_size)
        .all()
    )

    if not records:
        # Проверяем, есть ли вообще такая таблица у нас
        sheet_exists = (
            db.query(GoogleSheetRecord)
            .filter_by(
                sheet_id=sheet_id,
            )
            .first()
        )

        if not sheet_exists:
            raise HTTPException(
                status_code=404,
                detail=f"Google Sheet with ID {sheet_id} not found in database",
            )

        return {
            "message": "No unexported records available",
            "sheet_id": sheet_id,
            "remaining_records": 0,
        }

    # Формируем результат
    result = [record.row_data for record in records]

    # Помечаем как экспортированные
    for record in records:
        record.is_exported = True

    try:
        db.commit()

        # Получаем статистику по оставшимся записям
        remaining = (
            db.query(GoogleSheetRecord)
            .filter_by(
                sheet_id=sheet_id,
                is_exported=False,
            )
            .count()
        )

        return {
            "sheet_id": sheet_id,
            "count": len(result),
            "data": result,
            "remaining_records": remaining,
            "next_batch": f"/api/sheets/{sheet_id}/export?batch_size={batch_size}"
            if remaining > 0
            else None,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export data: {str(e)}",
        )
