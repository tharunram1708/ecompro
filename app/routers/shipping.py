from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AdminUser, DeliveryUser
from app.models import Order, ShippingDetail
from app.schemas import ShippingAssign, ShippingDetailOut, ShippingStatusUpdate
from app.services import assign_shipping, complete_delivery_if_needed, write_audit

router = APIRouter(prefix="/shipping", tags=["Shipping"])


@router.patch("/orders/{order_id}/assign", response_model=ShippingDetailOut)
def assign_delivery(
    order_id: int,
    payload: ShippingAssign,
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> ShippingDetail:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    shipping = assign_shipping(db, order, payload.delivery_partner_id, admin.id)
    db.commit()
    db.refresh(shipping)
    return shipping


@router.get("/assigned", response_model=list[ShippingDetailOut])
def assigned_deliveries(delivery_user: DeliveryUser, db: Annotated[Session, Depends(get_db)]) -> list[ShippingDetail]:
    return list(
        db.scalars(select(ShippingDetail).where(ShippingDetail.delivery_partner_id == delivery_user.id)).all()
    )


@router.patch("/{shipping_id}/status", response_model=ShippingDetailOut)
def update_delivery_status(
    shipping_id: int,
    payload: ShippingStatusUpdate,
    delivery_user: DeliveryUser,
    db: Annotated[Session, Depends(get_db)],
) -> ShippingDetail:
    shipping = db.get(ShippingDetail, shipping_id)
    if shipping is None or shipping.delivery_partner_id != delivery_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")

    shipping.delivery_status = payload.delivery_status
    complete_delivery_if_needed(db, shipping)
    write_audit(db, delivery_user.id, "UPDATE_DELIVERY_STATUS", f"shipping:{shipping.id}")
    db.commit()
    db.refresh(shipping)
    return shipping
