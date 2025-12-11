from pydantic import BaseModel
from datetime import datetime


class UserIn(BaseModel):
    tg_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    language_code: str | None = None


class UserOut(UserIn):
    created_at: datetime
    updated_at: datetime
    role: str = "user"
    is_banned: bool = False
