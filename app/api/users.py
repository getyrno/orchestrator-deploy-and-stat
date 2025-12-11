from fastapi import APIRouter
from app.services.users_store import ensure_user_exists, get_user_by_id
from app.schemas.users import UserIn, UserOut

router = APIRouter()


@router.post("/register", response_model=UserOut)
def register_user(user: UserIn):
    ensure_user_exists(
        tg_id=user.tg_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language=user.language_code,
    )
    return get_user_by_id(user.tg_id)


@router.get("/{tg_id}", response_model=UserOut)
def get_user(tg_id: int):
    return get_user_by_id(tg_id)
