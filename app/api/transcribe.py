from fastapi import APIRouter, BackgroundTasks
from app.schemas.transcribe import TranscribeEventIn
from app.services.transcribe_store import save_transcribe_event
from app.services.notifier.transcribe_notifier import send_transcribe_notification

router = APIRouter()


@router.post("")
async def collect_transcribe_event(ev: TranscribeEventIn, background_tasks: BackgroundTasks):

    def task():
        save_transcribe_event(ev)
        send_transcribe_notification(ev)

    background_tasks.add_task(task)
    return {"status": "ok"}
