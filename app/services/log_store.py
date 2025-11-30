# app/services/log_store.py
from __future__ import annotations
import json
import os
from typing import Any, Dict

from app.core.config import settings


def log_event(event: Dict[str, Any]) -> None:
    log_path = settings.deploy_log_path
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def get_latest_event() -> Dict[str, Any] | None:
    log_path = settings.deploy_log_path
    if not os.path.exists(log_path):
        return None

    last_line = ""
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                last_line = line

    if not last_line:
        return None

    return json.loads(last_line)
