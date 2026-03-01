"""Rider Application API — onboarding KYC submission, listing, and review."""

import logging
import uuid
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.database import get_db
from models.rider_application import RiderApplication
from models.rider import Rider
from models.warehouse import Warehouse
from schemas.rider_application import (
    RiderApplicationCreate,
    RiderApplicationResponse,
    ReviewAction,
)
from services import bot_notifier

router = APIRouter()
logger = logging.getLogger(__name__)


def _generate_employee_id(city_code: str, sequence: int) -> str:
    """Generate employee ID: EMP-{CITY_CODE}-{PADDED_NUMBER}."""
    return f"EMP-{city_code.upper()}-{sequence:02d}"


async def _next_employee_sequence(db: AsyncSession, city_code: str) -> int:
    """Get next employee sequence number for a city."""
    pattern = f"EMP-{city_code.upper()}-%"
    result = await db.execute(
        select(func.count(Rider.id)).where(Rider.employee_id.like(pattern))
    )
    count = result.scalar() or 0
    return count + 1


# ── POST /api/rider-applications ─────────────────────────

@router.post("/", response_model=RiderApplicationResponse, status_code=201)
async def create_application(
    data: RiderApplicationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Submit a new rider application from the Telegram bot."""
    # Check for existing application
    existing_result = await db.execute(
        select(RiderApplication).where(RiderApplication.telegram_id == data.telegram_id)
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        if existing.status == "REJECTED":
            # Allow re-application: reset the existing record with fresh data
            existing.full_name = data.full_name
            existing.phone = data.phone
            existing.email = data.email
            existing.vehicle = data.vehicle.value
            existing.vehicle_reg = data.vehicle_reg
            existing.license_file_id = data.license_file_id
            existing.license_file_url = data.license_file_url
            existing.aadhar_file_id = data.aadhar_file_id
            existing.aadhar_file_url = data.aadhar_file_url
            existing.preferred_warehouse_id = data.preferred_warehouse_id
            existing.status = "PENDING"
            existing.admin_note = None
            existing.reviewed_by = None
            existing.reviewed_at = None
            await db.commit()
            await db.refresh(existing)
            logger.info(
                "Rider re-application (was REJECTED): telegram_id=%s, name=%s",
                data.telegram_id, data.full_name,
            )
            await bot_notifier.notify_application_received(data.telegram_id)
            return existing
        else:
            raise HTTPException(
                status_code=409,
                detail="An application already exists for this Telegram ID",
            )

    # Check if already a rider
    existing_rider = await db.execute(
        select(Rider).where(Rider.telegram_id == data.telegram_id)
    )
    if existing_rider.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="This user is already registered as a rider",
        )

    application = RiderApplication(
        telegram_id=data.telegram_id,
        full_name=data.full_name,
        phone=data.phone,
        email=data.email,
        vehicle=data.vehicle.value,
        vehicle_reg=data.vehicle_reg,
        license_file_id=data.license_file_id,
        license_file_url=data.license_file_url,
        aadhar_file_id=data.aadhar_file_id,
        aadhar_file_url=data.aadhar_file_url,
        preferred_warehouse_id=data.preferred_warehouse_id,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)

    logger.info(
        "Rider application created: telegram_id=%s, name=%s, id=%s",
        data.telegram_id,
        data.full_name,
        application.id,
    )

    # Fire-and-forget notification to applicant
    await bot_notifier.notify_application_received(data.telegram_id)

    return application


# ── GET /api/rider-applications ──────────────────────────

@router.get("/", response_model=list[RiderApplicationResponse])
async def list_applications(
    status: str | None = Query(None, description="Filter by status: PENDING, APPROVED, REJECTED"),
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List all rider applications with optional status filter."""
    query = select(RiderApplication)
    if status:
        query = query.where(RiderApplication.status == status)
    query = query.order_by(RiderApplication.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


# ── GET /api/rider-applications/count ────────────────────

@router.get("/count")
async def count_applications(
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get count of applications, optionally filtered by status."""
    query = select(func.count(RiderApplication.id))
    if status:
        query = query.where(RiderApplication.status == status)
    result = await db.execute(query)
    return {"count": result.scalar() or 0}


# ── GET /api/rider-applications/telegram/{telegram_id} ───

@router.get("/telegram/{telegram_id}", response_model=RiderApplicationResponse | None)
async def get_application_by_telegram(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get an application by Telegram user ID (used by bot pre-checks)."""
    result = await db.execute(
        select(RiderApplication).where(RiderApplication.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


# ── GET /api/rider-applications/{id} ─────────────────────

@router.get("/{application_id}", response_model=RiderApplicationResponse)
async def get_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single rider application by ID."""
    result = await db.execute(
        select(RiderApplication).where(RiderApplication.id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


# ── PUT /api/rider-applications/{id}/review ──────────────

@router.put("/{application_id}/review", response_model=RiderApplicationResponse)
async def review_application(
    application_id: uuid.UUID,
    data: ReviewAction,
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject a rider application. On APPROVE, creates a rider record."""
    result = await db.execute(
        select(RiderApplication).where(RiderApplication.id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if application.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail=f"Application already reviewed (status: {application.status})",
        )

    application.reviewed_by = data.reviewed_by
    application.reviewed_at = datetime.utcnow()
    application.admin_note = data.admin_note

    if data.action == "APPROVE":
        application.status = "APPROVED"

        # Determine city code from preferred warehouse
        city_code = "GEN"  # default/generic
        if application.preferred_warehouse_id:
            wh_result = await db.execute(
                select(Warehouse).where(Warehouse.id == application.preferred_warehouse_id)
            )
            warehouse = wh_result.scalar_one_or_none()
            if warehouse and warehouse.city:
                # Use first 3 chars of city as code
                city_code = warehouse.city[:3].upper()

        # Generate employee ID
        seq = await _next_employee_sequence(db, city_code)
        employee_id = _generate_employee_id(city_code, seq)

        # Create rider record
        rider = Rider(
            telegram_id=application.telegram_id,
            employee_id=employee_id,
            full_name=application.full_name,
            phone=application.phone,
            vehicle=application.vehicle,
            vehicle_reg=application.vehicle_reg,
            warehouse_id=application.preferred_warehouse_id,
        )
        db.add(rider)

        logger.info(
            "Rider APPROVED: application_id=%s, employee_id=%s, telegram_id=%s",
            application_id,
            employee_id,
            application.telegram_id,
        )

        await db.commit()
        await db.refresh(application)

        # Notify rider of approval
        await bot_notifier.notify_application_approved(
            application.telegram_id,
            application.full_name,
            employee_id,
        )

    elif data.action == "REJECT":
        application.status = "REJECTED"

        logger.info(
            "Rider REJECTED: application_id=%s, telegram_id=%s, note=%s",
            application_id,
            application.telegram_id,
            data.admin_note,
        )

        await db.commit()
        await db.refresh(application)

        # Notify rider of rejection
        await bot_notifier.notify_application_rejected(
            application.telegram_id,
            data.admin_note,
        )

    return application


# ── GET /api/rider-applications/{id}/file/{doc_type} ─────

@router.get("/{application_id}/file/{doc_type}")
async def get_application_document(
    application_id: uuid.UUID,
    doc_type: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Proxy a Telegram-hosted KYC document for the admin dashboard.
    doc_type: 'license' or 'aadhar'
    Returns the raw image bytes so the bot token is never exposed to the browser.
    """
    result = await db.execute(
        select(RiderApplication).where(RiderApplication.id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if doc_type == "license":
        file_id = application.license_file_id
    elif doc_type == "aadhar":
        file_id = application.aadhar_file_id
    else:
        raise HTTPException(status_code=400, detail="doc_type must be 'license' or 'aadhar'")

    if not file_id:
        raise HTTPException(status_code=404, detail="Document not uploaded")

    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise HTTPException(status_code=503, detail="Bot token not configured")

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Step 1: resolve file_path from Telegram
        tg_resp = await client.get(
            f"https://api.telegram.org/bot{token}/getFile",
            params={"file_id": file_id},
        )
        if tg_resp.status_code != 200 or not tg_resp.json().get("ok"):
            raise HTTPException(status_code=502, detail="Failed to resolve file from Telegram")

        file_path = tg_resp.json()["result"]["file_path"]

        # Step 2: download the actual file
        file_resp = await client.get(
            f"https://api.telegram.org/file/bot{token}/{file_path}"
        )
        if file_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to download file from Telegram")

    content_type = file_resp.headers.get("content-type", "image/jpeg")
    return Response(
        content=file_resp.content,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )
