from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser
from app.models import Notification
from app.schemas import NotificationOut

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationOut])
def my_notifications(current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[Notification]:
    return list(
        db.scalars(select(Notification).where(Notification.user_id == current_user.id).order_by(Notification.id.desc())).all()
    )
