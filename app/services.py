from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    Address,
    AuditLog,
    Cart,
    Coupon,
    CouponUsage,
    DeliveryStatus,
    Inventory,
    Invoice,
    Notification,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentStatus,
    Product,
    Refund,
    RefundStatus,
    ReturnRequest,
    ReturnStatus,
    ShippingDetail,
    User,
    UserRole,
)


def money(value: Decimal | int | float) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def write_audit(db: Session, user_id: int | None, action: str, entity: str) -> None:
    db.add(AuditLog(user_id=user_id, action=action, entity=entity))


def notify(db: Session, user_id: int, title: str, message: str) -> None:
    db.add(Notification(user_id=user_id, title=title, message=message))


def get_or_create_cart(db: Session, customer_id: int) -> Cart:
    cart = db.scalar(select(Cart).where(Cart.customer_id == customer_id))
    if cart is None:
        cart = Cart(customer_id=customer_id)
        db.add(cart)
        db.flush()
    return cart


def require_product(db: Session, product_id: int) -> type[Product]:
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


def require_stock(product: Product, quantity: int) -> None:
    stock = product.inventory.stock_quantity if product.inventory else 0
    if stock < quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only {stock} item(s) available for {product.name}",
        )


def calculate_cart_totals(cart: Cart) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    settings = get_settings()
    subtotal = sum(money(item.product.price) * item.quantity for item in cart.items)
    discount = Decimal("0.00")
    if cart.coupon and cart.coupon.is_active:
        discount = money(subtotal * Decimal(cart.coupon.discount_percentage) / Decimal("100"))
    taxable_amount = max(subtotal - discount, Decimal("0.00"))
    tax = money(taxable_amount * Decimal(str(settings.tax_percentage)) / Decimal("100"))
    total = money(taxable_amount + tax)
    return money(subtotal), discount, tax, total


def apply_coupon_to_cart(db: Session, cart: Cart, customer_id: int, coupon_code: str) -> Cart:
    coupon = db.scalar(select(Coupon).where(Coupon.coupon_code == coupon_code, Coupon.is_active.is_(True)))
    if coupon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")

    used_before = db.scalar(
        select(CouponUsage).where(CouponUsage.coupon_id == coupon.id, CouponUsage.customer_id == customer_id)
    )
    if used_before:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Coupon already used")

    cart.coupon_id = coupon.id
    write_audit(db, customer_id, "APPLY_COUPON", f"coupon:{coupon.id}")
    return cart


def place_order_from_cart(db: Session, customer: User, address_id: int) -> Order:
    address = db.get(Address, address_id)
    if address is None or address.user_id != customer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")

    cart = get_or_create_cart(db, customer.id)
    if not cart.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

    for item in cart.items:
        require_stock(item.product, item.quantity)

    subtotal, discount, tax, total = calculate_cart_totals(cart)
    order = Order(customer_id=customer.id, total_amount=total, coupon_id=cart.coupon_id)
    db.add(order)
    db.flush()

    for item in cart.items:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.product.price,
            )
        )

    db.add(ShippingDetail(order_id=order.id, address_id=address.id))
    db.add(
        Invoice(
            order_id=order.id,
            invoice_number=f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{order.id:06d}",
            subtotal=subtotal,
            tax_amount=tax,
            discount_amount=discount,
            total_amount=total,
        )
    )

    if cart.coupon_id:
        db.add(CouponUsage(coupon_id=cart.coupon_id, customer_id=customer.id))

    for item in list(cart.items):
        db.delete(item)
    cart.coupon_id = None

    write_audit(db, customer.id, "PLACE_ORDER", f"order:{order.id}")
    notify(db, customer.id, "Order placed", f"Your order #{order.id} is waiting for payment.")
    return order


def mark_payment_success(db: Session, payment: Payment) -> None:
    order = payment.order
    if order.status != OrderStatus.PENDING_PAYMENT:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order is not waiting for payment")

    for item in order.items:
        inventory = db.scalar(select(Inventory).where(Inventory.product_id == item.product_id).with_for_update())
        if inventory is None or inventory.stock_quantity < item.quantity:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insufficient inventory")
        inventory.stock_quantity -= item.quantity

    payment.payment_status = PaymentStatus.SUCCESS
    order.status = OrderStatus.PAID
    order.paid_at = datetime.now(timezone.utc)
    write_audit(db, order.customer_id, "PAYMENT_SUCCESS", f"payment:{payment.id}")
    notify(db, order.customer_id, "Payment successful", f"Payment for order #{order.id} was received.")


def cancel_unpaid_orders(db: Session) -> int:
    expiry = datetime.now(timezone.utc) - timedelta(minutes=30)
    orders = db.scalars(
        select(Order).where(Order.status == OrderStatus.PENDING_PAYMENT, Order.created_at < expiry)
    ).all()
    for order in orders:
        order.status = OrderStatus.CANCELLED
        write_audit(db, order.customer_id, "AUTO_CANCEL_UNPAID_ORDER", f"order:{order.id}")
        notify(db, order.customer_id, "Order cancelled", f"Order #{order.id} was cancelled because payment timed out.")
    return len(orders)


def restore_order_stock(db: Session, order: Order) -> None:
    for item in order.items:
        inventory = db.scalar(select(Inventory).where(Inventory.product_id == item.product_id).with_for_update())
        if inventory:
            inventory.stock_quantity += item.quantity


def approve_return_and_refund(db: Session, return_request: ReturnRequest) -> Refund:
    order = return_request.order
    if order.payment is None or order.payment.payment_status != PaymentStatus.SUCCESS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No successful payment found")

    return_request.status = ReturnStatus.REFUNDED
    order.status = OrderStatus.RETURNED
    order.payment.payment_status = PaymentStatus.REFUNDED

    refund = Refund(
        payment_id=order.payment.id,
        refund_amount=order.payment.amount,
        refund_status=RefundStatus.PROCESSED,
    )
    db.add(refund)
    write_audit(db, order.customer_id, "RETURN_REFUNDED", f"return:{return_request.id}")
    notify(db, order.customer_id, "Refund processed", f"Refund for order #{order.id} has been processed.")
    return refund


def assign_shipping(db: Session, order: Order, delivery_partner_id: int, admin_id: int) -> ShippingDetail:
    partner = db.get(User, delivery_partner_id)
    if partner is None or partner.role != UserRole.DELIVERY_PARTNER:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery partner not found")

    shipping = order.shipping_detail
    if shipping is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipping detail not found")

    shipping.delivery_partner_id = delivery_partner_id
    shipping.delivery_status = DeliveryStatus.ASSIGNED
    order.status = OrderStatus.PROCESSING
    write_audit(db, admin_id, "ASSIGN_SHIPPING", f"order:{order.id}")
    notify(db, delivery_partner_id, "New delivery assigned", f"Order #{order.id} is assigned to you.")
    return shipping


def complete_delivery_if_needed(db: Session, shipping: ShippingDetail) -> None:
    if shipping.delivery_status == DeliveryStatus.DELIVERED:
        shipping.order.status = OrderStatus.DELIVERED
        notify(db, shipping.order.customer_id, "Delivered", f"Order #{shipping.order_id} was delivered.")
