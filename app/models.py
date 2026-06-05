from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    VENDOR = "VENDOR"
    CUSTOMER = "CUSTOMER"
    DELIVERY_PARTNER = "DELIVERY_PARTNER"


class OrderStatus(str, Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RETURN_REQUESTED = "RETURN_REQUESTED"
    RETURN_APPROVED = "RETURN_APPROVED"
    RETURNED = "RETURNED"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentMethod(str, Enum):
    CARD = "CARD"
    UPI = "UPI"
    NET_BANKING = "NET_BANKING"
    CASH_ON_DELIVERY = "CASH_ON_DELIVERY"


class DeliveryStatus(str, Enum):
    ASSIGNED = "ASSIGNED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class RefundStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PROCESSED = "PROCESSED"


class ReturnStatus(str, Enum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REFUNDED = "REFUNDED"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(80), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.CUSTOMER)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    addresses = relationship("Address", back_populates="user", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="vendor")
    cart = relationship("Cart", back_populates="customer", uselist=False, cascade="all, delete-orphan")
    wishlist = relationship("Wishlist", back_populates="customer", uselist=False, cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="customer")
    reviews = relationship("Review", back_populates="customer")


class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    address_line = Column(String(255), nullable=False)
    city = Column(String(80), nullable=False)
    state = Column(String(80), nullable=False)
    pincode = Column(String(20), nullable=False)

    user = relationship("User", back_populates="addresses")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)

    products = relationship("Product", back_populates="category")


class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)

    products = relationship("Product", back_populates="brand")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(180), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(12, 2), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    category = relationship("Category", back_populates="products")
    brand = relationship("Brand", back_populates="products")
    vendor = relationship("User", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    inventory = relationship("Inventory", back_populates="product", uselist=False, cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="product")


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    image_url = Column(String(500), nullable=False)

    product = relationship("Product", back_populates="images")


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, unique=True, index=True)
    stock_quantity = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    product = relationship("Product", back_populates="inventory")


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    coupon_id = Column(Integer, ForeignKey("coupons.id"), nullable=True)

    customer = relationship("User", back_populates="cart")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")
    coupon = relationship("Coupon")


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),)

    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)

    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")


class Wishlist(Base):
    __tablename__ = "wishlists"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    customer = relationship("User", back_populates="wishlist")
    items = relationship("WishlistItem", back_populates="wishlist", cascade="all, delete-orphan")


class WishlistItem(Base):
    __tablename__ = "wishlist_items"
    __table_args__ = (UniqueConstraint("wishlist_id", "product_id", name="uq_wishlist_product"),)

    id = Column(Integer, primary_key=True)
    wishlist_id = Column(Integer, ForeignKey("wishlists.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)

    wishlist = relationship("Wishlist", back_populates="items")
    product = relationship("Product")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    total_amount = Column(Numeric(12, 2), nullable=False)
    status = Column(SQLEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING_PAYMENT)
    coupon_id = Column(Integer, ForeignKey("coupons.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    customer = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    shipping_detail = relationship("ShippingDetail", back_populates="order", uselist=False, cascade="all, delete-orphan")
    payment = relationship("Payment", back_populates="order", uselist=False)
    invoice = relationship("Invoice", back_populates="order", uselist=False, cascade="all, delete-orphan")
    returns = relationship("ReturnRequest", back_populates="order")
    coupon = relationship("Coupon")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(12, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")


class ShippingDetail(Base):
    __tablename__ = "shipping_details"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True, index=True)
    address_id = Column(Integer, ForeignKey("addresses.id"), nullable=False)
    delivery_partner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    delivery_status = Column(SQLEnum(DeliveryStatus), nullable=False, default=DeliveryStatus.ASSIGNED)

    order = relationship("Order", back_populates="shipping_detail")
    address = relationship("Address")
    delivery_partner = relationship("User")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    payment_method = Column(SQLEnum(PaymentMethod), nullable=False)
    payment_status = Column(SQLEnum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    transaction_reference = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    order = relationship("Order", back_populates="payment")
    refunds = relationship("Refund", back_populates="payment")


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False, index=True)
    refund_amount = Column(Numeric(12, 2), nullable=False)
    refund_status = Column(SQLEnum(RefundStatus), nullable=False, default=RefundStatus.PENDING)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    payment = relationship("Payment", back_populates="refunds")


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("product_id", "customer_id", name="uq_product_customer_review"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating"),
    )

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    review_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    product = relationship("Product", back_populates="reviews")
    customer = relationship("User", back_populates="reviews")


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True)
    coupon_code = Column(String(40), nullable=False, unique=True, index=True)
    discount_percentage = Column(Numeric(5, 2), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    usages = relationship("CouponUsage", back_populates="coupon")


class CouponUsage(Base):
    __tablename__ = "coupon_usage"
    __table_args__ = (UniqueConstraint("coupon_id", "customer_id", name="uq_coupon_customer"),)

    id = Column(Integer, primary_key=True)
    coupon_id = Column(Integer, ForeignKey("coupons.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    coupon = relationship("Coupon", back_populates="usages")
    customer = relationship("User")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(120), nullable=False)
    message = Column(String(500), nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    user = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(120), nullable=False)
    entity = Column(String(120), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    user = relationship("User")


class ReturnRequest(Base):
    __tablename__ = "return_requests"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reason = Column(String(500), nullable=False)
    status = Column(SQLEnum(ReturnStatus), nullable=False, default=ReturnStatus.REQUESTED)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    order = relationship("Order", back_populates="returns")
    customer = relationship("User")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True, index=True)
    invoice_number = Column(String(80), nullable=False, unique=True)
    subtotal = Column(Numeric(12, 2), nullable=False)
    tax_amount = Column(Numeric(12, 2), nullable=False)
    discount_amount = Column(Numeric(12, 2), nullable=False, default=0)
    total_amount = Column(Numeric(12, 2), nullable=False)
    generated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    order = relationship("Order", back_populates="invoice")
