from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import (
    DeliveryStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    RefundStatus,
    ReturnStatus,
    UserRole,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole = UserRole.CUSTOMER


class UserOut(ORMModel):
    id: int
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool


class UserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class AddressCreate(BaseModel):
    address_line: str
    city: str
    state: str
    pincode: str


class AddressOut(AddressCreate, ORMModel):
    id: int
    user_id: int


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class CategoryOut(CategoryCreate, ORMModel):
    id: int


class BrandCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class BrandOut(BrandCreate, ORMModel):
    id: int


class ProductImageOut(ORMModel):
    id: int
    image_url: str


class InventoryOut(ORMModel):
    id: int
    product_id: int
    stock_quantity: int


class ProductCreate(BaseModel):
    category_id: int
    brand_id: int | None = None
    name: str = Field(min_length=2, max_length=180)
    description: str | None = None
    price: Decimal = Field(gt=0)
    stock_quantity: int = Field(ge=0)
    image_urls: list[str] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    category_id: int | None = None
    brand_id: int | None = None
    name: str | None = None
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    is_active: bool | None = None
    image_urls: list[str] | None = None


class ProductOut(ORMModel):
    id: int
    category_id: int
    brand_id: int | None
    vendor_id: int
    name: str
    description: str | None
    price: Decimal
    is_active: bool
    images: list[ProductImageOut] = []
    inventory: InventoryOut | None = None


class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0)


class CouponApply(BaseModel):
    coupon_code: str


class CartItemOut(ORMModel):
    id: int
    product_id: int
    quantity: int
    product: ProductOut


class CartOut(ORMModel):
    id: int
    customer_id: int
    coupon_id: int | None
    items: list[CartItemOut] = []


class WishlistItemOut(ORMModel):
    id: int
    product_id: int
    product: ProductOut


class WishlistOut(ORMModel):
    id: int
    customer_id: int
    items: list[WishlistItemOut] = []


class OrderCreate(BaseModel):
    address_id: int


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderItemOut(ORMModel):
    id: int
    product_id: int
    quantity: int
    price: Decimal


class ShippingAssign(BaseModel):
    delivery_partner_id: int


class ShippingStatusUpdate(BaseModel):
    delivery_status: DeliveryStatus


class ShippingDetailOut(ORMModel):
    id: int
    order_id: int
    address_id: int
    delivery_partner_id: int | None
    delivery_status: DeliveryStatus


class InvoiceOut(ORMModel):
    id: int
    order_id: int
    invoice_number: str
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    generated_at: datetime


class OrderOut(ORMModel):
    id: int
    customer_id: int
    total_amount: Decimal
    status: OrderStatus
    coupon_id: int | None
    created_at: datetime
    paid_at: datetime | None
    items: list[OrderItemOut] = []
    shipping_detail: ShippingDetailOut | None = None
    invoice: InvoiceOut | None = None


class PaymentCreate(BaseModel):
    order_id: int
    payment_method: PaymentMethod
    mark_success: bool = True
    transaction_reference: str | None = None


class PaymentOut(ORMModel):
    id: int
    order_id: int
    amount: Decimal
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    transaction_reference: str | None


class RefundCreate(BaseModel):
    payment_id: int
    refund_amount: Decimal = Field(gt=0)


class RefundOut(ORMModel):
    id: int
    payment_id: int
    refund_amount: Decimal
    refund_status: RefundStatus


class ReviewCreate(BaseModel):
    product_id: int
    rating: int = Field(ge=1, le=5)
    review_text: str | None = None


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    review_text: str | None = None


class ReviewOut(ORMModel):
    id: int
    product_id: int
    customer_id: int
    rating: int
    review_text: str | None
    created_at: datetime


class InventoryUpdate(BaseModel):
    stock_quantity: int = Field(ge=0)


class CouponCreate(BaseModel):
    coupon_code: str = Field(min_length=3, max_length=40)
    discount_percentage: Decimal = Field(ge=0, le=100)
    is_active: bool = True


class CouponOut(CouponCreate, ORMModel):
    id: int


class NotificationOut(ORMModel):
    id: int
    user_id: int
    title: str
    message: str
    is_read: bool
    created_at: datetime


class ReturnCreate(BaseModel):
    order_id: int
    reason: str = Field(min_length=5, max_length=500)


class ReturnDecision(BaseModel):
    approve: bool


class ReturnOut(ORMModel):
    id: int
    order_id: int
    customer_id: int
    reason: str
    status: ReturnStatus
    created_at: datetime


class ReportRow(BaseModel):
    label: str
    value: Decimal | int


class VendorSalesRow(BaseModel):
    vendor_id: int
    product_id: int
    product_name: str
    units_sold: int
    revenue: Decimal


class CustomerPurchaseRow(BaseModel):
    customer_id: int
    orders: int
    total_spent: Decimal
