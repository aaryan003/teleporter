import uuid

from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID

from api.models.base import Base


class DeliveryRoute(Base):
    __tablename__ = "delivery_routes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rider_id = Column(UUID(as_uuid=True), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(String(20), default="PLANNED")
    optimized_sequence = Column(JSONB, nullable=False)
    total_distance_km = Column(String, nullable=True)
    total_duration_min = Column(Integer, nullable=True)
    total_parcels = Column(Integer, nullable=True)
    started_at = Column(TIMESTAMP, nullable=True)
    completed_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False)

