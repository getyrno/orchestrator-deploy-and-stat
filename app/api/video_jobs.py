from fastapi import APIRouter, BackgroundTasks
from app.schemas.video_jobs import VideoJobEventIn
from app.services.video_job.video_jobs_store import save_video_job_event
from app.services.video_job.video_job_notifier import send_video_job_notification

router = APIRouter()


@router.post("")
async def push_video_job_event(ev: VideoJobEventIn, background_tasks: BackgroundTasks):

    def task():
        save_video_job_event(ev)
        send_video_job_notification(ev)

    background_tasks.add_task(task)
    return {"status": "ok"}
