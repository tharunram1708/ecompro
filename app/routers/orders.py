from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AdminUser, CustomerUser
from app.models import Order, OrderStatus, ReturnRequest, ReturnStatus
from app.schemas import OrderCreate, OrderOut, OrderStatusUpdate, ReturnCreate, ReturnDecision, ReturnOut
from app.services import approve_return_and_refund, cancel_unpaid_orders, place_order_from_cart, restore_order_stock, write_audit

router = APIRouter(prefix="/orders", tags=["Orders"])
returns_router = APIRouter(prefix="/returns", tags=["Returns"])


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def place_order(payload: OrderCreate, customer: CustomerUser, db: Annotated[Session, Depends(get_db)]) -> Order:
    order = place_order_from_cart(db, customer, payload.address_id)
    db.commit()
    db.refresh(order)
    return order


@router.get("", response_model=list[OrderOut])
def order_history(customer: CustomerUser, db: Annotated[Session, Depends(get_db)]) -> list[Order]:
    cancel_unpaid_orders(db)
    db.commit()
    return list(db.scalars(select(Order).where(Order.customer_id == customer.id).order_by(Order.id.desc())).all())


@router.get("/admin/all", response_model=list[OrderOut])
def list_all_orders(_: AdminUser, db: Annotated[Session, Depends(get_db)]) -> list[Order]:
    return list(db.scalars(select(Order).order_by(Order.id.desc())).all())


@router.patch("/admin/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order.status = payload.status
    write_audit(db, admin.id, "UPDATE_ORDER_STATUS", f"order:{order.id}")
    db.commit()
    db.refresh(order)
    return order


@router.post("/maintenance/auto-cancel-unpaid")
def auto_cancel_unpaid(_: AdminUser, db: Annotated[Session, Depends(get_db)]) -> dict[str, int]:
    count = cancel_unpaid_orders(db)
    db.commit()
    return {"cancelled_orders": count}


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, customer: CustomerUser, db: Annotated[Session, Depends(get_db)]) -> Order:
    order = db.get(Order, order_id)
    if order is None or order.customer_id != customer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.patch("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: int, customer: CustomerUser, db: Annotated[Session, Depends(get_db)]) -> Order:
    order = db.get(Order, order_id)
    if order is None or order.customer_id != customer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status not in {OrderStatus.PENDING_PAYMENT, OrderStatus.PAID, OrderStatus.PROCESSING}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order can no longer be cancelled")

    if order.status in {OrderStatus.PAID, OrderStatus.PROCESSING}:
        restore_order_stock(db, order)
    order.status = OrderStatus.CANCELLED
    write_audit(db, customer.id, "CANCEL_ORDER", f"order:{order.id}")
    db.commit()
    db.refresh(order)
    return order


@returns_router.post("", response_model=ReturnOut, status_code=status.HTTP_201_CREATED)
def request_return(payload: ReturnCreate, customer: CustomerUser, db: Annotated[Session, Depends(get_db)]) -> ReturnRequest:
    order = db.get(Order, payload.order_id)
    if order is None or order.customer_id != customer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only delivered orders can be returned")

    order.status = OrderStatus.RETURN_REQUESTED
    return_request = ReturnRequest(order_id=order.id, customer_id=customer.id, reason=payload.reason)
    db.add(return_request)
    write_audit(db, customer.id, "REQUEST_RETURN", f"order:{order.id}")
    db.commit()
    db.refresh(return_request)
    return return_request


@returns_router.patch("/{return_id}/decision", response_model=ReturnOut)
def decide_return(
    return_id: int,
    payload: ReturnDecision,
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> ReturnRequest:
    return_request = db.get(ReturnRequest, return_id)
    if return_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return request not found")
    if return_request.status != ReturnStatus.REQUESTED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Return already decided")

    if payload.approve:
        return_request.status = ReturnStatus.APPROVED
        return_request.order.status = OrderStatus.RETURN_APPROVED
        approve_return_and_refund(db, return_request)
    else:
        return_request.status = ReturnStatus.REJECTED

    write_audit(db, admin.id, "DECIDE_RETURN", f"return:{return_request.id}")
    db.commit()
    db.refresh(return_request)
    return return_request
