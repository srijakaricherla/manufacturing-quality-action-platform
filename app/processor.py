import hashlib
from dataclasses import dataclass
from datetime import timezone

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import QualityAction, QualityEvent, QualityRule
from .schemas import EventIn


@dataclass
class ProcessResult:
    event_id: str
    status: str
    quality_result: str | None = None
    action_id: str | None = None
    reason: str | None = None


def evaluate(value: float, lower: float, upper: float) -> str:
    return "PASS" if lower <= value <= upper else "FAIL"


def process_event(db: Session, payload: EventIn) -> ProcessResult:
    if db.get(QualityEvent, payload.event_id):
        return ProcessResult(payload.event_id, "DUPLICATE", reason="event_id already processed")

    rule = db.scalar(
        select(QualityRule)
        .where(
            QualityRule.test_name == payload.test_name,
            QualityRule.station_id == payload.station_id,
            QualityRule.active.is_(True),
        )
        .order_by(desc(QualityRule.id))
    )
    if not rule:
        return ProcessResult(payload.event_id, "REJECTED", reason="no active quality rule")

    latest = db.scalar(
        select(QualityEvent)
        .where(QualityEvent.unit_id == payload.unit_id, QualityEvent.test_name == payload.test_name)
        .order_by(desc(QualityEvent.source_timestamp))
    )
    latest_timestamp = latest.source_timestamp if latest else None
    if latest_timestamp and latest_timestamp.tzinfo is None:
        latest_timestamp = latest_timestamp.replace(tzinfo=timezone.utc)
    stale = bool(latest_timestamp and latest_timestamp >= payload.timestamp)
    quality_result = evaluate(payload.value, rule.lower_limit, rule.upper_limit)
    reason = (
        f"value {payload.value} {payload.unit} within [{rule.lower_limit}, {rule.upper_limit}]"
        if quality_result == "PASS"
        else f"value {payload.value} {payload.unit} outside [{rule.lower_limit}, {rule.upper_limit}]"
    )
    if stale:
        reason += "; retained for traceability, no disposition change"

    event = QualityEvent(
        event_id=payload.event_id,
        unit_id=payload.unit_id,
        station_id=payload.station_id,
        equipment_id=payload.equipment_id,
        test_name=payload.test_name,
        value=payload.value,
        measurement_unit=payload.unit,
        source_timestamp=payload.timestamp,
        source=payload.source,
        result=quality_result,
        rule_version=rule.version,
        decision_reason=reason,
        stale=stale,
    )
    db.add(event)

    action = None
    if quality_result == "FAIL" and not stale:
        action_id = hashlib.sha256(f"{payload.event_id}:{rule.failure_action}".encode()).hexdigest()[:24]
        action = QualityAction(
            action_id=action_id,
            event_id=payload.event_id,
            unit_id=payload.unit_id,
            action_type=rule.failure_action,
            status="PENDING",
        )
        db.add(action)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return ProcessResult(payload.event_id, "DUPLICATE", reason="concurrent duplicate prevented")

    return ProcessResult(
        payload.event_id,
        "PROCESSED",
        quality_result=quality_result,
        action_id=action.action_id if action else None,
        reason=reason,
    )
