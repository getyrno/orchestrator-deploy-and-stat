# app/schemas/model_stat.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel


class ModelStatEvent(BaseModel):
    """
    То, что шлёт ML-сервис на /trigger/model_stat.
    """
    event_type: str  # "model_stat"
    env: str         # gpu-prod / staging / etc
    timestamp: datetime
    service: str     # "ml-service-voice-trans"
    data: Dict[str, Any]  # внутри: summaries + raw results
