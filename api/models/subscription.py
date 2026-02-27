"""Subscription ORM model — revenue plan tracking."""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Numeric, Boolean, DateTime, ForeignKey, Enum as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    plan: Mapped[str] = mapped_column(
        PgEnum("STARTER", "BUSINESS", "ENTERPRISE", name="subscription_plan", create_type=False),
        nullable=False,
    )
    monthly_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    free_deliveries_total: Mapped[int] = mapped_column(Integer, default=0)
    free_deliveries_used: Mapped[int] = mapped_column(Integer, default=0)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    razorpay_subscription_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="subscriptions", lazy="selectin")
