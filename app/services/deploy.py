# app/services/deploy.py
from __future__ import annotations

import datetime as dt
import subprocess
import time
import uuid
from typing import Any, Dict, Optional
import os

import requests

from app.core.config import settings
from app.services.notifier.telegram_notifier import send_deploy_start_notification


def now_utc_msk() -> tuple[str, str]:
    utc = dt.datetime.now(dt.timezone.utc)
    msk = utc + dt.timedelta(hours=3)
    return (
        utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        msk.strftime("%Y-%m-%dT%H:%M:%S+03:00"),
    )


def run_ssh_deploy() -> Dict[str, Any]:
    """
    Запуск деплоя на домашний ПК через SSH.
    ВО ВСЕХ ВЕТКАХ возвращает словарь с ключами:
    returncode, stdout, stderr, duration_ms
    """

    if os.getenv("DRY_RUN_DEPLOY") == "1":
        time.sleep(0.3)
        return {
            "returncode": 0,
            "stdout": "[DRY_RUN] ssh deploy skipped, pretending success",
            "stderr": "",
            "duration_ms": 600,
        }

    # 👇 ТУТ ОСНОВНОЕ ИЗМЕНЕНИЕ: явный путь /home/getyrno/... и немного дебага
    remote_cmd = (
        'wsl.exe -d Ubuntu -- /usr/bin/env bash -lc '
        '"set -xe; '                               # x - лог команд, e - падать по первой ошибке
        'cd /home/getyrno/ml-service-voice-trans '  # ⚠️ ЯВНЫЙ ПУТЬ
        '&& git fetch origin main '
        '&& git reset --hard origin/main '
        '&& (docker compose down --remove-orphans || true) '
        '&& docker system prune -af --volumes '
        '&& docker compose up -d --build"'
    )

    ssh_cmd = [
        "ssh",
        "-i",
        settings.home_ssh_key_path,
        "-o",
        "StrictHostKeyChecking=no",
        f"{settings.home_ssh_user}@{settings.home_ssh_host}",
        remote_cmd,
    ]

    start = time.time()
    try:
        proc = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=1800,
        )
        duration = int((time.time() - start) * 1000)
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "duration_ms": duration,
        }
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "duration_ms": duration,
        }

def run_healthcheck() -> Dict[str, Any]:
    """
    Healthcheck приложения.
    В DRY-RUN режиме тоже всегда успешный.
    Возвращает словарь с ключами:
    status_code, duration_ms, error
    """

    # В dev-режиме можно не долбить реальный сервис
    if os.getenv("DRY_RUN_DEPLOY") == "1":
        return {
            "status_code": 200,
            "duration_ms": 0,
            "error": None,
        }

    start = time.time()
    try:
        r = requests.get(settings.healthcheck_url, timeout=5)
        duration = int((time.time() - start) * 1000)
        return {"status_code": r.status_code, "duration_ms": duration, "error": None}
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        return {"status_code": 0, "duration_ms": duration, "error": str(e)}


def build_deploy_event(
    payload: Dict[str, Any],
    deploy_id: str,
    result: str,
    stage: Optional[str],
    error_message: Optional[str],
    ssh_info: Dict[str, Any],
    hc_info: Dict[str, Any],
) -> Dict[str, Any]:
    utc, msk = now_utc_msk()

    repo = payload.get("repository", {}).get("full_name")
    ref = payload.get("ref")
    commit_full = payload.get("after") or ""
    commit_sha = commit_full[:7]
    actor = payload.get("pusher", {}).get("name")

    return {
        "event_type": "deploy",
        "deploy_id": deploy_id,
        "timestamps": {"utc": utc, "msk": msk},
        "env": {"name": settings.env_name},
        "git": {
            "repo": repo,
            "branch": ref,
            "commit_sha": commit_sha,
            "actor": actor,
        },
        "targets": {
            "vds": {"host": settings.vds_hostname},
            "home_pc": {
                "vpn_ip": settings.home_ssh_host,
                "ssh_user": settings.home_ssh_user,
            },
        },
        "deploy": {
            "ssh_returncode": ssh_info.get("returncode"),
            "ssh_duration_ms": ssh_info.get("duration_ms"),
        },
        "healthcheck": {
            "url": settings.healthcheck_url,
            "status_code": hc_info.get("status_code"),
            "duration_ms": hc_info.get("duration_ms"),
            "error": hc_info.get("error"),
        },
        "status": {
            "result": result,          # success | failed
            "failed_stage": stage,     # ssh | healthcheck | None
            "error_message": error_message,
        },
    }


def do_deploy(payload: Dict[str, Any]) -> Dict[str, Any]:
    deploy_id = str(uuid.uuid4())
    stages = []

    # 1) START
    push_stage(stages, "deploy_start")
    try:
        send_deploy_start_notification(payload)
        push_stage(stages, "telegram_start", "ok")
    except Exception as e:
        push_stage(stages, "telegram_start", "failed", str(e))

    # 2) SSH deploy
    push_stage(stages, "ssh_deploy")
    ssh_info = run_ssh_deploy()
    if ssh_info.get("returncode") != 0:
        push_stage(stages, "ssh_deploy", "failed", ssh_info.get("stderr"))
        result = "failed"
        stage = "ssh"
        error_message = ssh_info.get("stderr")
        hc_info = {"status_code": 0, "duration_ms": 0, "error": None}
    else:
        push_stage(stages, "ssh_deploy", "ok")

        # 3) Healthcheck
        push_stage(stages, "healthcheck")
        hc_info = run_healthcheck()

        if hc_info.get("status_code") == 200:
            push_stage(stages, "healthcheck", "ok")
            result = "success"
            stage = None
            error_message = None
        else:
            push_stage(stages, "healthcheck", "failed", hc_info.get("error"))
            result = "failed"
            stage = "healthcheck"
            error_message = hc_info.get("error") or f"status_code={hc_info.get('status_code')}"

    # 4) END
    push_stage(stages, "deploy_end", "ok" if result == "success" else "failed")

    # 5) собираем полное событие
    event = build_deploy_event(
        payload=payload,
        deploy_id=deploy_id,
        result=result,
        stage=stage,
        error_message=error_message,
        ssh_info=ssh_info,
        hc_info=hc_info,
    )

    # 👇 добавляем этапы в event
    event["stages"] = stages

    return event


def push_stage(stages: list[dict], name: str, status: str = "start", info: str = None):
    utc = dt.datetime.now(dt.timezone.utc)
    msk = utc + dt.timedelta(hours=3)

    stages.append({
        "stage": name,
        "status": status,   # start | ok | failed
        "info": info,
        "utc": utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "msk": msk.strftime("%Y-%m-%d %H:%M:%S"),
    })
