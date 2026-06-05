from fastapi import FastAPI

from app.database import create_tables
from app.routers import (
    auth,
    cart,
    inventory,
    notifications,
    orders,
    payments,
    products,
    reports,
    reviews,
    shipping,
    users,
)


app = FastAPI(
    title="ECOMPRO - Enterprise E-Commerce Order Management System",
    version="1.0.0",
    description="Backend-only FastAPI service for e-commerce order management.",
)


@app.on_event("startup")
def on_startup() -> None:
    create_tables()


@app.get("/health", tags=["System"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(products.catalog_router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(cart.wishlist_router)
app.include_router(orders.router)
app.include_router(orders.returns_router)
app.include_router(payments.router)
app.include_router(reviews.router)
app.include_router(inventory.router)
app.include_router(shipping.router)
app.include_router(notifications.router)
app.include_router(reports.router)
