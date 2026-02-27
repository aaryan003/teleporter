import uuid

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID

from api.models.base import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    address = Column(String, nullable=False)
    lat = Column(String, nullable=False)
    lng = Column(String, nullable=False)
    city = Column(String(100), nullable=True)
    capacity = Column(Integer, default=500)
    current_load = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    operating_hours = Column(JSONB, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False)

