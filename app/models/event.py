from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, text
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.models.base import Base

class Event(Base):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    job_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    step: Mapped[str] = mapped_column(String, nullable=False)          # e.g., plan, act
    status: Mapped[str] = mapped_column(String, nullable=False)        # started/finished/failed
    payload_json = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("NOW()"))
