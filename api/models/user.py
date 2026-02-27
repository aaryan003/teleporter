import uuid

from sqlalchemy import BigInteger, Column, String
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

from api.models.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    full_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    created_at = Column(TIMESTAMP, nullable=False)

