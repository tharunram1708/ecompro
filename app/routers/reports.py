from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AdminUser, CurrentUser
from app.models import Order, OrderItem, OrderStatus, Product, UserRole
from app.schemas import CustomerPurchaseRow, ReportRow, VendorSalesRow

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/top-selling-products", response_model=list[ReportRow])
def top_selling_products(_: AdminUser, db: Annotated[Session, Depends(get_db)]) -> list[ReportRow]:
    rows = db.execute(
        select(Product.name, func.sum(OrderItem.quantity))
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]))
        .group_by(Product.id)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(10)
    ).all()
    return [ReportRow(label=name, value=int(units or 0)) for name, units in rows]


@router.get("/monthly-revenue", response_model=list[ReportRow])
def monthly_revenue(
    _: AdminUser,
    db: Annotated[Session, Depends(get_db)],
    year: int | None = None,
) -> list[ReportRow]:
    selected_year = year or datetime.utcnow().year
    rows = db.execute(
        select(extract("month", Order.paid_at), func.sum(Order.total_amount))
        .where(Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]))
        .where(extract("year", Order.paid_at) == selected_year)
        .group_by(extract("month", Order.paid_at))
        .order_by(extract("month", Order.paid_at))
    ).all()
    return [ReportRow(label=f"{selected_year}-{int(month):02d}", value=Decimal(total or 0)) for month, total in rows]


@router.get("/vendor-sales", response_model=list[VendorSalesRow])
def vendor_sales_report(current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[VendorSalesRow]:
    query = (
        select(
            Product.vendor_id,
            Product.id,
            Product.name,
            func.sum(OrderItem.quantity),
            func.sum(OrderItem.quantity * OrderItem.price),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]))
        .group_by(Product.vendor_id, Product.id)
    )
    if current_user.role == UserRole.VENDOR:
        query = query.where(Product.vendor_id == current_user.id)
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    rows = db.execute(query).all()
    return [
        VendorSalesRow(
            vendor_id=vendor_id,
            product_id=product_id,
            product_name=name,
            units_sold=int(units or 0),
            revenue=Decimal(revenue or 0),
        )
        for vendor_id, product_id, name, units, revenue in rows
    ]


@router.get("/customer-purchases", response_model=list[CustomerPurchaseRow])
def customer_purchase_report(_: AdminUser, db: Annotated[Session, Depends(get_db)]) -> list[CustomerPurchaseRow]:
    rows = db.execute(
        select(Order.customer_id, func.count(Order.id), func.sum(Order.total_amount))
        .where(Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]))
        .group_by(Order.customer_id)
        .order_by(func.sum(Order.total_amount).desc())
    ).all()
    return [
        CustomerPurchaseRow(customer_id=customer_id, orders=int(count or 0), total_spent=Decimal(total or 0))
        for customer_id, count, total in rows
    ]
