import uuid

from sqlalchemy import BigInteger, Column, Integer, String
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

from api.models.base import Base


class Rider(Base):
    __tablename__ = "riders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    employee_id = Column(String(20), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    vehicle_type = Column(String(20), nullable=False)
    vehicle_reg = Column(String(20), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), nullable=True)
    current_lat = Column(String, nullable=True)
    current_lng = Column(String, nullable=True)
    status = Column(String(20), nullable=False, default="OFF_DUTY")
    shift_start = Column(TIMESTAMP, nullable=True)
    shift_end = Column(TIMESTAMP, nullable=True)
    max_capacity = Column(Integer, default=5)
    current_load = Column(Integer, default=0)
    rating = Column(String, nullable=True)
    total_deliveries = Column(Integer, default=0)
    last_location_update = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False)

