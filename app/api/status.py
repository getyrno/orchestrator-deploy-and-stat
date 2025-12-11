from fastapi import APIRouter, HTTPException
from app.services.log_store import get_latest_event

router = APIRouter()

@router.get("/latest")
def latest_deploy():
    event = get_latest_event()
    if not event:
        raise HTTPException(status_code=404, detail="No deploy logs yet")
    return event
