from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.db.database import engine
from api.models.base import Base
from api.routers import orders, payments, riders, users, warehouses, webhooks


def create_app() -> FastAPI:
    app = FastAPI(title="TeleporterBot API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(users.router)
    app.include_router(riders.router)
    app.include_router(warehouses.router)
    app.include_router(orders.router)
    app.include_router(payments.router)
    app.include_router(webhooks.router)

    @app.on_event("startup")
    async def on_startup() -> None:
        # Ensure metadata is bound so Alembic or manual migrations can run
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @app.get("/")
    async def root():
        return {"message": "TeleporterBot API running"}

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

