# app/services/telegram/model_stat_notifier.py
from __future__ import annotations

import html
import io
from typing import Any, Dict

import matplotlib.pyplot as plt

from app.core.config import settings
from app.schemas.model_stat import ModelStatEvent
from app.services.telegram.telegram_sender import send_telegram_message


def _num(d: Dict[str, Any], key: str, default: float = 0.0) -> float:
    v = d.get(key)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def send_model_stat_notification(ev: ModelStatEvent) -> None:
    data = ev.data or {}
    ws = data.get("whisper_summary") or {}
    gs = data.get("gigaam_summary") or {}

    # Числа
    ws_total = ws.get("total_files", 0)
    ws_ok = ws.get("successful", 0)
    ws_rtf = _num(ws, "realtime_factor")
    ws_avg = _num(ws, "avg_time_sec")

    gs_total = gs.get("total_files", 0)
    gs_ok = gs.get("successful", 0)
    gs_rtf = _num(gs, "realtime_factor")
    gs_avg = _num(gs, "avg_time_sec")

    # Короткий caption
    ts = ev.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    text = (
        f"📊 <b>STT benchmark</b>\n"
        f"<code>{html.escape(ev.env)}</code> · "
        f"<code>{html.escape(ev.service)}</code>\n"
        f"🕒 {html.escape(ts)}\n\n"
        f"Whisper: {ws_ok}/{ws_total}, RTF={ws_rtf:.2f}x\n"
        f"GigaAM: {gs_ok}/{gs_total}, RTF={gs_rtf:.2f}x"
    )

    # ===== Рисуем график =====
    models = ["Whisper", "GigaAM"]
    avg_times = [ws_avg, gs_avg]
    rtfs = [ws_rtf, gs_rtf]

    fig, axes = plt.subplots(1, 2, figsize=(8, 4))

    # avg time
    ax1 = axes[0]
    ax1.bar(models, avg_times)
    ax1.set_title("Avg time, s")
    for i, v in enumerate(avg_times):
        ax1.text(i, v, f"{v:.2f}", ha="center", va="bottom", fontsize=8)

    # RTF
    ax2 = axes[1]
    ax2.bar(models, rtfs)
    ax2.set_title("RTF (lower is faster)")
    for i, v in enumerate(rtfs):
        ax2.text(i, v, f"{v:.2f}", ha="center", va="bottom", fontsize=8)

    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    png_bytes = buf.getvalue()
    buf.close()

    files = {
        "document": ("stt_benchmark.png", png_bytes),
    }

    send_telegram_message(
        token=settings.all_eat_bot_token,
        chat_id=settings.all_eat_chat_id,
        text=text,
        files=files,
    )
