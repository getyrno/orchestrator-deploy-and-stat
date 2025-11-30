# app/services/telegram_notifier.py
from __future__ import annotations

from typing import Any, Dict
import requests
import textwrap

from app.core.config import settings


def _format_deploy_message(event: Dict[str, Any]) -> str:
    status = event.get("status", {})
    result = status.get("result")
    is_ok = result == "success"

    emoji = "✅" if is_ok else "❌"
    env_name = event.get("env", {}).get("name", "-")
    git = event.get("git", {}) or {}
    repo = git.get("repo") or "manual"
    branch = git.get("branch") or "-"
    sha = git.get("commit_sha") or "-"
    actor = git.get("actor") or "-"

    ts = event.get("timestamps", {}) or {}
    utc = ts.get("utc") or "-"
    msk = ts.get("msk") or "-"

    hc = event.get("healthcheck", {}) or {}
    hc_url = hc.get("url") or "-"
    hc_code = hc.get("status_code")
    hc_ms = hc.get("duration_ms")

    deploy = event.get("deploy", {}) or {}
    ssh_rc = deploy.get("ssh_returncode")
    ssh_ms = deploy.get("ssh_duration_ms")

    failed_stage = status.get("failed_stage") or "-"
    err = status.get("error_message") or "-"

    text = f"""
    {emoji} Deploy {result.upper()} [{env_name}]

    🧾 Repo:   {repo}
    🌿 Branch: {branch}
    🔖 Commit: {sha}
    👤 Actor:  {actor}

    🕒 Time UTC: {utc}
    🕒 Time MSK: {msk}

    🖥 VDS host:  {event.get("targets", {}).get("vds", {}).get("host", "-")}
    🏠 Home PC:   {event.get("targets", {}).get("home_pc", {}).get("vpn_ip", "-")} ({event.get("targets", {}).get("home_pc", {}).get("ssh_user", "-")})

    🔌 SSH: rc={ssh_rc}, ~{ssh_ms} ms
    ❤️ Healthcheck: {hc_url}
       code={hc_code}, ~{hc_ms} ms

    🧩 Failed stage: {failed_stage}
    🐞 Error: {err}
    """
    # убираем общий отступ
    return textwrap.dedent(text).strip()


def send_deploy_notification(event: Dict[str, Any]) -> None:
    """
    Шлём уведомление в Telegram.
    Если не настроен TELEGRAM_BOT_TOKEN/CHAT_ID — тихо выходим.
    """
    if not settings.telegram_enabled:
        return

    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id

    text = _format_deploy_message(event)

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",  # по сути у нас обычный текст, но ок
    }

    try:
        resp = requests.post(url, json=payload, timeout=5)
        # можем логировать ошибки, но оркестратор из-за этого падать не должен
        if resp.status_code != 200:
            # на будущее можно писать в лог-файл
            print(f"[telegram] send failed: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[telegram] exception while sending: {e}")
