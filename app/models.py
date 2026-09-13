from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow():
    return datetime.now(timezone.utc)


class QualityRule(Base):
    __tablename__ = "quality_rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_name: Mapped[str] = mapped_column(String(100), nullable=False)
    station_id: Mapped[str] = mapped_column(String(100), nullable=False)
    lower_limit: Mapped[float] = mapped_column(Float, nullable=False)
    upper_limit: Mapped[float] = mapped_column(Float, nullable=False)
    failure_action: Mapped[str] = mapped_column(String(50), default="HOLD_AND_RETEST")
    version: Mapped[str] = mapped_column(String(20), default="v1")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("test_name", "station_id", "version"),)


class QualityEvent(Base):
    __tablename__ = "quality_events"
    event_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    unit_id: Mapped[str] = mapped_column(String(100), index=True)
    station_id: Mapped[str] = mapped_column(String(100))
    equipment_id: Mapped[str] = mapped_column(String(100))
    test_name: Mapped[str] = mapped_column(String(100), index=True)
    value: Mapped[float] = mapped_column(Float)
    measurement_unit: Mapped[str] = mapped_column(String(30))
    source_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source: Mapped[str] = mapped_column(String(100))
    result: Mapped[str] = mapped_column(String(30))
    rule_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    decision_reason: Mapped[str] = mapped_column(Text)
    stale: Mapped[bool] = mapped_column(Boolean, default=False)


class QualityAction(Base):
    __tablename__ = "quality_actions"
    action_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("quality_events.event_id"), index=True)
    unit_id: Mapped[str] = mapped_column(String(100), index=True)
    action_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

