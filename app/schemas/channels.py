from pydantic import BaseModel


class ChannelCreate(BaseModel):
    model_config = {
        "protected_namespaces": ()
    }
    user_id: int
    channel: str


class ChannelOut(BaseModel):
    model_config = {
        "protected_namespaces": ()
    }
    id: str
    user_id: int
    channel: str
    is_active: bool
