from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import QualityAction, QualityEvent, QualityRule
from app.processor import evaluate, process_event
from app.schemas import EventIn


def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(QualityRule(test_name="bolt_torque", station_id="S1", lower_limit=40, upper_limit=45, failure_action="HOLD_AND_RETEST", version="v1"))
    db.commit()
    return db


def payload(event_id="E1", value=42, timestamp=None):
    return EventIn(event_id=event_id, unit_id="U1", station_id="S1", equipment_id="T1", test_name="bolt_torque", value=value, unit="Nm", timestamp=timestamp or datetime.now(timezone.utc), source="test")


def test_inclusive_boundaries():
    assert evaluate(40, 40, 45) == "PASS"
    assert evaluate(45, 40, 45) == "PASS"
    assert evaluate(46, 40, 45) == "FAIL"


def test_failure_creates_one_idempotent_action():
    db = session()
    first = process_event(db, payload(value=48))
    second = process_event(db, payload(value=48))
    assert first.quality_result == "FAIL"
    assert first.action_id
    assert second.status == "DUPLICATE"
    assert len(db.scalars(select(QualityAction)).all()) == 1


def test_out_of_order_event_is_stored_without_action():
    db = session()
    now = datetime.now(timezone.utc)
    process_event(db, payload("NEW", 42, now))
    result = process_event(db, payload("OLD", 48, now - timedelta(minutes=5)))
    old = db.get(QualityEvent, "OLD")
    assert result.quality_result == "FAIL"
    assert old.stale is True
    assert result.action_id is None


def test_missing_rule_is_rejected():
    db = session()
    item = payload()
    item.test_name = "unknown"
    assert process_event(db, item).status == "REJECTED"

