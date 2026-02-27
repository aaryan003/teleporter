"""
TeleporterBot v2 — FastAPI Backend
Hub-and-Spoke Logistics Management System
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db.database import engine, Base
from routers import orders, riders, users, payments, admin, warehouses, webhooks


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    print("🚀 TeleporterBot API starting...")
    yield
    # Shutdown
    await engine.dispose()
    print("🛑 TeleporterBot API shut down.")


app = FastAPI(
    title="TeleporterBot Logistics API",
    description="Hub-and-Spoke delivery management system backend",
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(riders.router, prefix="/api/riders", tags=["Riders"])
app.include_router(warehouses.router, prefix="/api/warehouses", tags=["Warehouses"])
app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin Dashboard"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["n8n Webhooks"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "TeleporterBot API v2"}
