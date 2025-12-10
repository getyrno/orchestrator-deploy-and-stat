# app/main.py
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Dict

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from app.schemas.model_stat import ModelStatEvent
from app.schemas.video_jobs import VideoJobEventIn
from app.schemas.transcribe import TranscribeEventIn
from app.core.config import settings
from app.services.deploy import do_deploy
from app.services.deploy import do_deploy
from app.services.log_store import get_latest_event, log_event
from app.services.log_store import get_latest_event, log_event
from app.services.db.migrations import apply_all_migrations
from app.services.transcribe_store import save_transcribe_event
from app.services.video_job.video_job_notifier import send_video_job_notification
from app.services.video_job.video_jobs_store import save_video_job_event
from app.services.notifier.model_stat_notifier import send_model_stat_notification
from app.services.notifier.transcribe_notifier import send_transcribe_notification
from app.services.notifier.telegram_notifier import send_deploy_notification  # 👈 вот это

app = FastAPI(title="Deploy Orchestrator")


import logging
logger = logging.getLogger(__name__)

@app.on_event("startup")
def on_startup():
    try:
        apply_all_migrations()
    except Exception as e:
        # Не кладём весь сервис, просто логируем
        logger.exception(f"apply_all_migrations failed: {e}")


def verify_github_signature(body: bytes, signature_header: str | None) -> bool:
    secret = settings.github_webhook_secret
    if not secret:
        # dev-режим, можно вернуть True, но в проде лучше падать
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    signature = signature_header.split("=", 1)[1]
    mac = hmac.new(secret.encode("utf-8"), msg=body, digestmod=hashlib.sha256)
    expected = mac.hexdigest()
    return hmac.compare_digest(expected, signature)


@app.get("/status/latest")
def latest_deploy():
    event = get_latest_event()
    if not event:
        raise HTTPException(status_code=404, detail="No deploy logs yet")
    return event


@app.post("/deploy/manual")
def manual_deploy(background_tasks: BackgroundTasks):
    """
    Ручной триггер деплоя без GitHub (для теста/ручного запуска).
    """
    def task():
        dummy_payload: Dict[str, Any] = {
            "repository": {"full_name": "manual"},
            "ref": "manual",
            "after": "",
            "pusher": {"name": "manual"},
        }
        event = do_deploy(dummy_payload)
        log_event(event)
        send_deploy_notification(event)  # 🔔

    background_tasks.add_task(task)
    return {"status": "accepted"}

@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256")

    if not verify_github_signature(body, sig):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event_type = request.headers.get("X-GitHub-Event")
    if event_type != "push":
        return {"status": "ignored", "reason": f"event {event_type} not handled"}

    payload = await request.json()
    ref = payload.get("ref")
    repo = payload.get("repository", {}).get("full_name")

    if repo != settings.github_repo or ref != "refs/heads/main":
        return {"status": "ignored", "reason": f"repo/ref mismatch: {repo} {ref}"}

    def task():
        event = do_deploy(payload)
        log_event(event)
        send_deploy_notification(event)  # 🔔

    background_tasks.add_task(task)
    return {"status": "accepted"}

@app.post("/events/transcribe")
async def collect_transcribe_event(
    ev: TranscribeEventIn,
    background_tasks: BackgroundTasks,
):
    """
    ML-сервис на домашнем ПК шлёт сюда событие после транскрибации.
    Мы:
      1) пишем его в Postgres
      2) (опционально) шлём нотификацию во второго телеграм-бота
    """

    def task():
        save_transcribe_event(ev)
        send_transcribe_notification(ev)

    background_tasks.add_task(task)
    return {"status": "ok"}

@app.post("/events/transcribe/job")
async def push_video_job_event(
    ev: VideoJobEventIn,
    background_tasks: BackgroundTasks,
):
    """
    ML-сервис шлёт сюда события по видео-джобам (этапы пайплайна).
    Мы:
      1) складываем событие и job в Postgres
      2) шлём телеграм-уведомление для финальных статусов (DONE/FAIL/TIMEOUT)
    """

    def task():
        save_video_job_event(ev)
        send_video_job_notification(ev)

    background_tasks.add_task(task)
    return {"status": "ok"}


@app.post("/trigger/model_stat")
async def handle_model_stat(
    ev: ModelStatEvent,
    background_tasks: BackgroundTasks,
):
    """
    ML-сервис шлёт сюда результаты бенчмарка моделей.

    Мы:
      - ничего не храним (пока),
      - в фоне шлём нотификацию в all-eat бота.
    """

    def task():
        try:
            send_model_stat_notification(ev)
        except Exception:
            # На всякий случай, чтобы вообще НИЧЕГО не положило процесс.
            logger.exception("handle_model_stat: failed to send model_stat notification")

    background_tasks.add_task(task)
    return {"status": "ok"}