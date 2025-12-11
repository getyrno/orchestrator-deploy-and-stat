from fastapi import FastAPI
from app.api.router import api_router
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Deploy Orchestrator")

@app.on_event("startup")
def on_startup():
    pass

app.include_router(api_router)
