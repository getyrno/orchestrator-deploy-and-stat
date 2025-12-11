import logging
from fastapi import APIRouter, BackgroundTasks
from app.schemas.model_stat import ModelStatEvent
from app.services.notifier.model_stat_notifier import send_model_stat_notification

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/model_stat")
async def handle_model_stat(ev: ModelStatEvent, background_tasks: BackgroundTasks):

    def task():
        try:
            send_model_stat_notification(ev)
        except Exception:
            logger.exception("model_stat: failed to send notification")

    background_tasks.add_task(task)
    return {"status": "ok"}
