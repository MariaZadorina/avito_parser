from datetime import datetime

from fastapi import APIRouter

from database import SessionLocal
from schedule.models import TaskSchedule
from schedule.service import run_scheduled_task
from schedule.service import scheduler

schedule_router = APIRouter()


@schedule_router.get("/scheduler/jobs")
def list_scheduled_jobs():
    """Список всех задач в планировщике"""
    status = "запущен" if scheduler.running else "остановлен"
    return [
        {"id": job.id, "next_run": str(job.next_run_time), "status": status}
        for job in scheduler.get_jobs()
    ]


@schedule_router.post("/tasks/{task_id}/run")
def run_task_now(task_id: int):
    """Ручной запуск задачи"""
    db = SessionLocal()
    task = db.query(TaskSchedule).get(task_id)
    if not task:
        return {"error": "Task not found"}

    # Запускаем вручную (без ожидания интервала)
    scheduler.add_job(
        run_scheduled_task,
        args=[db, task],
        id=f"manual_{task.task_name}",
        next_run_time=datetime.now(),
    )
    return {"status": "Task started"}
