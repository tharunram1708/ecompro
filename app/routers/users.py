from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AdminUser, CurrentUser
from app.models import Address, User
from app.schemas import AddressCreate, AddressOut, UserOut, UserUpdate
from app.services import write_audit

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
def me(current_user: CurrentUser) -> User:
    return current_user


@router.get("", response_model=list[UserOut])
def list_users(_: AdminUser, db: Annotated[Session, Depends(get_db)]) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)).all())


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active

    write_audit(db, admin.id, "UPDATE_USER", f"user:{user.id}")
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/addresses", response_model=AddressOut, status_code=status.HTTP_201_CREATED)
def add_address(
    payload: AddressCreate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> Address:
    address = Address(user_id=current_user.id, **payload.model_dump())
    db.add(address)
    write_audit(db, current_user.id, "ADD_ADDRESS", "address")
    db.commit()
    db.refresh(address)
    return address


@router.get("/me/addresses", response_model=list[AddressOut])
def list_my_addresses(current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[Address]:
    return list(db.scalars(select(Address).where(Address.user_id == current_user.id)).all())
