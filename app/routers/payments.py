from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CustomerUser
from app.models import Order, Payment, PaymentStatus, Refund
from app.schemas import PaymentCreate, PaymentOut, RefundCreate, RefundOut
from app.services import mark_payment_success, write_audit

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(payload: PaymentCreate, customer: CustomerUser, db: Annotated[Session, Depends(get_db)]) -> Payment:
    order = db.get(Order, payload.order_id)
    if order is None or order.customer_id != customer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.payment:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment already exists for this order")

    payment = Payment(
        order_id=order.id,
        amount=order.total_amount,
        payment_method=payload.payment_method,
        payment_status=PaymentStatus.PENDING,
        transaction_reference=payload.transaction_reference,
    )
    db.add(payment)
    db.flush()

    if payload.mark_success:
        mark_payment_success(db, payment)

    write_audit(db, customer.id, "CREATE_PAYMENT", f"order:{order.id}")
    db.commit()
    db.refresh(payment)
    return payment


@router.post("/refunds", response_model=RefundOut, status_code=status.HTTP_201_CREATED)
def refund_payment(payload: RefundCreate, customer: CustomerUser, db: Annotated[Session, Depends(get_db)]) -> Refund:
    payment = db.get(Payment, payload.payment_id)
    if payment is None or payment.order.customer_id != customer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    if payment.payment_status != PaymentStatus.SUCCESS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only successful payments can be refunded")
    if payload.refund_amount > payment.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refund exceeds payment amount")

    refund = Refund(payment_id=payment.id, refund_amount=payload.refund_amount)
    db.add(refund)
    write_audit(db, customer.id, "REQUEST_REFUND", f"payment:{payment.id}")
    db.commit()
    db.refresh(refund)
    return refund
