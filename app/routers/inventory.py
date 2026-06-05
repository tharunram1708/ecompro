from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import CurrentUser, VendorUser
from app.models import Inventory, Product, UserRole
from app.schemas import InventoryOut, InventoryUpdate
from app.services import write_audit

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.patch("/products/{product_id}", response_model=InventoryOut)
def update_stock(
    product_id: int,
    payload: InventoryUpdate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> Inventory:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if current_user.role != UserRole.ADMIN and product.vendor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update stock")

    inventory = product.inventory
    if inventory is None:
        inventory = Inventory(product_id=product.id, stock_quantity=0)
        db.add(inventory)
    inventory.stock_quantity = payload.stock_quantity
    write_audit(db, current_user.id, "UPDATE_STOCK", f"product:{product.id}")
    db.commit()
    db.refresh(inventory)
    return inventory


@router.get("/low-stock", response_model=list[InventoryOut])
def low_stock_alerts(current_user: VendorUser, db: Annotated[Session, Depends(get_db)]) -> list[Inventory]:
    settings = get_settings()
    query = select(Inventory).join(Product).where(Inventory.stock_quantity <= settings.low_stock_threshold)
    if current_user.role == UserRole.VENDOR:
        query = query.where(Product.vendor_id == current_user.id)
    return list(db.scalars(query.order_by(Inventory.stock_quantity.asc())).all())
