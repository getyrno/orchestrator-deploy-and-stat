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
from app.services.telegram_notifier import send_deploy_start_notification


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

    # DRY-RUN режим: не делаем реальный ssh, просто "удачный" ответ
    if os.getenv("DRY_RUN_DEPLOY") == "1":
        time.sleep(0.3)
        return {
            "returncode": 0,
            "stdout": "[DRY_RUN] ssh deploy skipped, pretending success",
            "stderr": "",
            "duration_ms": 300,
        }

    ssh_cmd = [
        "ssh",
        "-i",
        settings.home_ssh_key_path,
        "-o",
        "StrictHostKeyChecking=no",
        f"{settings.home_ssh_user}@{settings.home_ssh_host}",
        'wsl -d Ubuntu -- bash -lc "cd ~/ml-service-voice-trans && git pull origin main && docker compose up -d --build"',
    ]
    start = time.time()
    try:
        proc = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=900,
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
    try:
        send_deploy_start_notification(payload)
    except Exception as e:
        print(f"[deploy] failed to send start notification: {e}")
    ssh_info = run_ssh_deploy()

    stage: Optional[str] = None
    error_message: Optional[str] = None

    if ssh_info.get("returncode") != 0:
        result = "failed"
        stage = "ssh"
        error_message = ssh_info.get("stderr")
        hc_info = {"status_code": 0, "duration_ms": 0, "error": None}
    else:
        hc_info = run_healthcheck()
        if hc_info.get("status_code") == 200:
            result = "success"
        else:
            result = "failed"
            stage = "healthcheck"
            error_message = hc_info.get("error") or f"status_code={hc_info.get('status_code')}"

    event = build_deploy_event(payload, deploy_id, result, stage, error_message, ssh_info, hc_info)
    return event
