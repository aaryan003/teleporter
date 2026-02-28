"""
TeleporterBot v2 — FastAPI Backend
Hub-and-Spoke Logistics Management System
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
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


@app.get("/health/db")
async def health_db():
    """Verify DB connection and that we're talking to the right database."""
    from sqlalchemy import text
    from db.database import engine
    try:
        async with engine.connect() as conn:
            row = (await conn.execute(text("SELECT current_database(), current_user"))).first()
            db_name, db_user = row[0], row[1]
            count_row = (await conn.execute(text("SELECT COUNT(*) FROM users"))).first()
            user_count = count_row[0] if count_row else 0
        return {
            "status": "ok",
            "database": db_name,
            "user": db_user,
            "users_count": user_count,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/debug/geocode")
async def debug_geocode(address: str = Query("12/A Tulsi Villa, Maninagar, Ahmedabad - 380058")):
    """Test geocoding — helps verify GEOAPIFY_API_KEY and address parsing."""
    from services.maps import geocode
    from config import settings
    result = await geocode(address)
    return {
        "address": address,
        "geoapify_key_set": bool(settings.GEOAPIFY_API_KEY),
        "result": result,
    }
