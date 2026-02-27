import uuid

from sqlalchemy import Column, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

from api.models.base import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    plan = Column(String(20), nullable=False)
    monthly_price = Column(Numeric(10, 2), nullable=False)
    free_deliveries_remaining = Column(Integer, default=0)
    starts_at = Column(TIMESTAMP, nullable=False)
    expires_at = Column(TIMESTAMP, nullable=False)
    is_active = Column(String, default="true")
    razorpay_subscription_id = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, nullable=False)

