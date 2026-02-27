"""AI Insight ORM model — AI-generated dashboard analytics."""

from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, JSON, Enum as PgEnum
from sqlalchemy.orm import Mapped, mapped_column
from db.database import Base


class AIInsight(Base):
    __tablename__ = "ai_insights"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(
        PgEnum("INFO", "WARNING", "ACTION_REQUIRED", name="insight_severity", create_type=False),
        default="INFO",
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    insight: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict | None] = mapped_column(JSON, default={})
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
