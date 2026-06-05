from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AdminUser, CurrentUser, VendorUser
from app.models import Brand, Category, Inventory, Product, ProductImage, UserRole
from app.schemas import (
    BrandCreate,
    BrandOut,
    CategoryCreate,
    CategoryOut,
    CouponCreate,
    CouponOut,
    ProductCreate,
    ProductOut,
    ProductUpdate,
)
from app.models import Coupon
from app.services import write_audit

router = APIRouter(prefix="/products", tags=["Products"])
catalog_router = APIRouter(prefix="/catalog", tags=["Catalog"])


@catalog_router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, admin: AdminUser, db: Annotated[Session, Depends(get_db)]) -> Category:
    category = Category(**payload.model_dump())
    db.add(category)
    write_audit(db, admin.id, "CREATE_CATEGORY", payload.name)
    db.commit()
    db.refresh(category)
    return category


@catalog_router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Annotated[Session, Depends(get_db)]) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.name)).all())


@catalog_router.post("/brands", response_model=BrandOut, status_code=status.HTTP_201_CREATED)
def create_brand(payload: BrandCreate, admin: AdminUser, db: Annotated[Session, Depends(get_db)]) -> Brand:
    brand = Brand(**payload.model_dump())
    db.add(brand)
    write_audit(db, admin.id, "CREATE_BRAND", payload.name)
    db.commit()
    db.refresh(brand)
    return brand


@catalog_router.get("/brands", response_model=list[BrandOut])
def list_brands(db: Annotated[Session, Depends(get_db)]) -> list[Brand]:
    return list(db.scalars(select(Brand).order_by(Brand.name)).all())


@catalog_router.post("/coupons", response_model=CouponOut, status_code=status.HTTP_201_CREATED)
def create_coupon(payload: CouponCreate, admin: AdminUser, db: Annotated[Session, Depends(get_db)]) -> Coupon:
    coupon = Coupon(**payload.model_dump())
    db.add(coupon)
    write_audit(db, admin.id, "CREATE_COUPON", payload.coupon_code)
    db.commit()
    db.refresh(coupon)
    return coupon


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def add_product(
    payload: ProductCreate,
    current_user: VendorUser,
    db: Annotated[Session, Depends(get_db)],
) -> Product:
    vendor_id = current_user.id
    product = Product(
        category_id=payload.category_id,
        brand_id=payload.brand_id,
        vendor_id=vendor_id,
        name=payload.name,
        description=payload.description,
        price=payload.price,
    )
    db.add(product)
    db.flush()
    db.add(Inventory(product_id=product.id, stock_quantity=payload.stock_quantity))
    for image_url in payload.image_urls:
        db.add(ProductImage(product_id=product.id, image_url=image_url))

    write_audit(db, current_user.id, "ADD_PRODUCT", f"product:{product.id}")
    db.commit()
    db.refresh(product)
    return product


@router.get("", response_model=list[ProductOut])
def search_products(
    db: Annotated[Session, Depends(get_db)],
    q: str | None = Query(default=None, description="Search by product name or description"),
    category_id: int | None = None,
    brand_id: int | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
) -> list[Product]:
    query = select(Product).where(Product.is_active.is_(True))
    if q:
        pattern = f"%{q}%"
        query = query.where(Product.name.ilike(pattern) | Product.description.ilike(pattern))
    if category_id:
        query = query.where(Product.category_id == category_id)
    if brand_id:
        query = query.where(Product.brand_id == brand_id)
    if min_price is not None:
        query = query.where(Product.price >= min_price)
    if max_price is not None:
        query = query.where(Product.price <= max_price)
    return list(db.scalars(query.order_by(Product.id.desc())).all())


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Annotated[Session, Depends(get_db)]) -> Product:
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if current_user.role != UserRole.ADMIN and product.vendor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update this product")

    updates = payload.model_dump(exclude_unset=True, exclude={"image_urls"})
    for field, value in updates.items():
        setattr(product, field, value)

    if payload.image_urls is not None:
        for image in list(product.images):
            db.delete(image)
        for image_url in payload.image_urls:
            db.add(ProductImage(product_id=product.id, image_url=image_url))

    write_audit(db, current_user.id, "UPDATE_PRODUCT", f"product:{product.id}")
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> None:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if current_user.role != UserRole.ADMIN and product.vendor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to delete this product")

    product.is_active = False
    write_audit(db, current_user.id, "DELETE_PRODUCT", f"product:{product.id}")
    db.commit()
