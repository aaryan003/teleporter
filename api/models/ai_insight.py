from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP

from api.models.base import Base


class AIInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50), nullable=False)
    insight = Column(Text, nullable=False)
    severity = Column(String(20), default="INFO")
    data = Column(JSONB, nullable=True)
    generated_at = Column(TIMESTAMP, nullable=False)
    expires_at = Column(TIMESTAMP, nullable=True)

