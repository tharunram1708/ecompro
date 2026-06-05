from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CustomerUser
from app.models import CartItem, Product, Wishlist, WishlistItem
from app.schemas import CartItemCreate, CartItemUpdate, CartOut, CouponApply, WishlistOut
from app.services import apply_coupon_to_cart, get_or_create_cart, require_product, require_stock, write_audit

router = APIRouter(prefix="/cart", tags=["Cart"])
wishlist_router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


@router.get("", response_model=CartOut)
def get_cart(customer: CustomerUser, db: Annotated[Session, Depends(get_db)]) -> object:
    return get_or_create_cart(db, customer.id)


@router.post("/items", response_model=CartOut, status_code=status.HTTP_201_CREATED)
def add_to_cart(
    payload: CartItemCreate,
    customer: CustomerUser,
    db: Annotated[Session, Depends(get_db)],
) -> object:
    product = require_product(db, payload.product_id)
    require_stock(product, payload.quantity)

    cart = get_or_create_cart(db, customer.id)
    item = db.scalar(select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product.id))
    if item:
        item.quantity += payload.quantity
        require_stock(product, item.quantity)
    else:
        db.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=payload.quantity))

    write_audit(db, customer.id, "ADD_TO_CART", f"product:{product.id}")
    db.commit()
    db.refresh(cart)
    return cart


@router.patch("/items/{item_id}", response_model=CartOut)
def update_quantity(
    item_id: int,
    payload: CartItemUpdate,
    customer: CustomerUser,
    db: Annotated[Session, Depends(get_db)],
) -> object:
    cart = get_or_create_cart(db, customer.id)
    item = db.scalar(select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id))
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    require_stock(item.product, payload.quantity)
    item.quantity = payload.quantity
    write_audit(db, customer.id, "UPDATE_CART_QUANTITY", f"cart_item:{item.id}")
    db.commit()
    db.refresh(cart)
    return cart


@router.delete("/items/{item_id}", response_model=CartOut)
def remove_from_cart(item_id: int, customer: CustomerUser, db: Annotated[Session, Depends(get_db)]) -> object:
    cart = get_or_create_cart(db, customer.id)
    item = db.scalar(select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id))
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    db.delete(item)
    write_audit(db, customer.id, "REMOVE_FROM_CART", f"cart_item:{item.id}")
    db.commit()
    db.refresh(cart)
    return cart


@router.post("/apply-coupon", response_model=CartOut)
def apply_coupon(payload: CouponApply, customer: CustomerUser, db: Annotated[Session, Depends(get_db)]) -> object:
    cart = get_or_create_cart(db, customer.id)
    apply_coupon_to_cart(db, cart, customer.id, payload.coupon_code)
    db.commit()
    db.refresh(cart)
    return cart


def get_or_create_wishlist(db: Session, customer_id: int) -> Wishlist:
    wishlist = db.scalar(select(Wishlist).where(Wishlist.customer_id == customer_id))
    if wishlist is None:
        wishlist = Wishlist(customer_id=customer_id)
        db.add(wishlist)
        db.flush()
    return wishlist


@wishlist_router.get("", response_model=WishlistOut)
def get_wishlist(customer: CustomerUser, db: Annotated[Session, Depends(get_db)]) -> Wishlist:
    return get_or_create_wishlist(db, customer.id)


@wishlist_router.post("/{product_id}", response_model=WishlistOut)
def add_to_wishlist(product_id: int, customer: CustomerUser, db: Annotated[Session, Depends(get_db)]) -> Wishlist:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    wishlist = get_or_create_wishlist(db, customer.id)
    exists = db.scalar(
        select(WishlistItem).where(WishlistItem.wishlist_id == wishlist.id, WishlistItem.product_id == product_id)
    )
    if exists is None:
        db.add(WishlistItem(wishlist_id=wishlist.id, product_id=product_id))
    write_audit(db, customer.id, "ADD_TO_WISHLIST", f"product:{product_id}")
    db.commit()
    db.refresh(wishlist)
    return wishlist


@wishlist_router.delete("/{product_id}", response_model=WishlistOut)
def remove_from_wishlist(product_id: int, customer: CustomerUser, db: Annotated[Session, Depends(get_db)]) -> Wishlist:
    wishlist = get_or_create_wishlist(db, customer.id)
    item = db.scalar(
        select(WishlistItem).where(WishlistItem.wishlist_id == wishlist.id, WishlistItem.product_id == product_id)
    )
    if item:
        db.delete(item)
        write_audit(db, customer.id, "REMOVE_FROM_WISHLIST", f"product:{product_id}")
    db.commit()
    db.refresh(wishlist)
    return wishlist
