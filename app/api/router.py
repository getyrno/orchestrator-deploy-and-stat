from fastapi import APIRouter

from app.api import (
    status,
    transcribe,
    video_jobs,
    model_stat,
    users, 
    channels
)


api_router = APIRouter()

api_router.include_router(
    status.router,
    prefix="/status",
    tags=["status"]
)

api_router.include_router(
    transcribe.router,
    prefix="/events/transcribe",
    tags=["transcribe"]
)

api_router.include_router(
    video_jobs.router,
    prefix="/events/transcribe/job",
    tags=["video-jobs"]
)

api_router.include_router(
    model_stat.router,
    prefix="/trigger",
    tags=["model-stat"]
)
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)

api_router.include_router(
    channels.router,
    prefix="/channels",
    tags=["channels"]
)
