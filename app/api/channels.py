from fastapi import APIRouter
from uuid import uuid4
from app.services.channels_store import (
    ensure_channel_exists,
    get_channels_by_user,
    deactivate_channel,
)
from app.schemas.channels import ChannelCreate, ChannelOut

router = APIRouter()


@router.post("/create", response_model=ChannelOut)
def create_channel(body: ChannelCreate):
    channel_id = ensure_channel_exists(body.user_id, body.channel)
    return {
        "id": channel_id,
        "user_id": body.user_id,
        "channel": body.channel,
        "is_active": True,
    }


@router.get("/list/{user_id}", response_model=list[ChannelOut])
def list_channels(user_id: int):
    return get_channels_by_user(user_id)


@router.post("/deactivate")
def deactivate_channel_route(channel_id: str):
    deactivate_channel(channel_id)
    return {"status": "ok"}
