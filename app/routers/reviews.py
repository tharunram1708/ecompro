from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CustomerUser
from app.models import Order, OrderItem, OrderStatus, Review
from app.schemas import ReviewCreate, ReviewOut, ReviewUpdate
from app.services import require_product, write_audit

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def add_review(payload: ReviewCreate, customer: CustomerUser, db: Annotated[Session, Depends(get_db)]) -> Review:
    require_product(db, payload.product_id)
    duplicate = db.scalar(
        select(Review).where(Review.product_id == payload.product_id, Review.customer_id == customer.id)
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already reviewed this product")

    delivered_order = db.scalar(
        select(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .where(
            Order.customer_id == customer.id,
            Order.status == OrderStatus.DELIVERED,
            OrderItem.product_id == payload.product_id,
        )
    )
    if delivered_order is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only delivered products can be reviewed")

    review = Review(customer_id=customer.id, **payload.model_dump())
    db.add(review)
    write_audit(db, customer.id, "ADD_REVIEW", f"product:{payload.product_id}")
    db.commit()
    db.refresh(review)
    return review


@router.patch("/{review_id}", response_model=ReviewOut)
def edit_review(
    review_id: int,
    payload: ReviewUpdate,
    customer: CustomerUser,
    db: Annotated[Session, Depends(get_db)],
) -> Review:
    review = db.get(Review, review_id)
    if review is None or review.customer_id != customer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(review, field, value)

    write_audit(db, customer.id, "EDIT_REVIEW", f"review:{review.id}")
    db.commit()
    db.refresh(review)
    return review


@router.get("/products/{product_id}", response_model=list[ReviewOut])
def list_product_reviews(product_id: int, db: Annotated[Session, Depends(get_db)]) -> list[Review]:
    return list(db.scalars(select(Review).where(Review.product_id == product_id).order_by(Review.id.desc())).all())
