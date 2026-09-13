from pathlib import Path
from time import perf_counter

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from .db import Base, SessionLocal, engine, get_db
from .models import QualityAction, QualityEvent, QualityRule
from .processor import process_event
from .schemas import EventIn, RuleIn

app = FastAPI(title="Manufacturing Quality Action Platform", version="1.0.0")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
EVENTS = Counter("quality_events_total", "Events received", ["status", "result"])
LATENCY = Histogram("quality_processing_seconds", "Event processing latency")


@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        existing = db.scalar(select(QualityRule).limit(1))
        if not existing:
            db.add_all([
                QualityRule(test_name="bolt_torque", station_id="STATION-12", lower_limit=40, upper_limit=45, failure_action="HOLD_AND_RETEST", version="v1"),
                QualityRule(test_name="surface_temperature", station_id="THERMAL-01", lower_limit=15, upper_limit=80, failure_action="HOLD_AND_ALERT", version="v1"),
            ])
            db.commit()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/events")
def ingest_event(payload: EventIn, db: Session = Depends(get_db)):
    started = perf_counter()
    result = process_event(db, payload)
    LATENCY.observe(perf_counter() - started)
    EVENTS.labels(result.status, result.quality_result or "NONE").inc()
    if result.status == "REJECTED":
        raise HTTPException(422, result.reason)
    return result.__dict__


@app.get("/api/events")
def list_events(limit: int = 100, db: Session = Depends(get_db)):
    rows = db.scalars(select(QualityEvent).order_by(desc(QualityEvent.received_at)).limit(min(limit, 500))).all()
    return [
        {
            "event_id": x.event_id, "unit_id": x.unit_id, "station_id": x.station_id,
            "test_name": x.test_name, "value": x.value, "unit": x.measurement_unit,
            "result": x.result, "rule_version": x.rule_version, "stale": x.stale,
            "reason": x.decision_reason, "timestamp": x.source_timestamp,
        } for x in rows
    ]


@app.get("/api/actions")
def list_actions(limit: int = 100, db: Session = Depends(get_db)):
    rows = db.scalars(select(QualityAction).order_by(desc(QualityAction.created_at)).limit(min(limit, 500))).all()
    return [
        {"action_id": x.action_id, "event_id": x.event_id, "unit_id": x.unit_id,
         "action_type": x.action_type, "status": x.status, "attempts": x.attempts,
         "last_error": x.last_error} for x in rows
    ]


@app.get("/api/units/{unit_id}")
def unit_history(unit_id: str, db: Session = Depends(get_db)):
    events = db.scalars(select(QualityEvent).where(QualityEvent.unit_id == unit_id).order_by(QualityEvent.source_timestamp)).all()
    actions = db.scalars(select(QualityAction).where(QualityAction.unit_id == unit_id).order_by(QualityAction.created_at)).all()
    if not events:
        raise HTTPException(404, "unit not found")
    return {
        "unit_id": unit_id,
        "events": [{"event_id": e.event_id, "test_name": e.test_name, "value": e.value, "result": e.result, "stale": e.stale, "reason": e.decision_reason} for e in events],
        "actions": [{"action_id": a.action_id, "type": a.action_type, "status": a.status, "attempts": a.attempts} for a in actions],
    }


@app.get("/api/rules")
def list_rules(db: Session = Depends(get_db)):
    return db.scalars(select(QualityRule).order_by(QualityRule.id)).all()


@app.post("/api/rules")
def create_rule(payload: RuleIn, db: Session = Depends(get_db)):
    rule = QualityRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"id": rule.id, **payload.model_dump()}


@app.get("/api/summary")
def summary(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(QualityEvent)) or 0
    failed = db.scalar(select(func.count()).select_from(QualityEvent).where(QualityEvent.result == "FAIL")) or 0
    stale = db.scalar(select(func.count()).select_from(QualityEvent).where(QualityEvent.stale.is_(True))) or 0
    pending = db.scalar(select(func.count()).select_from(QualityAction).where(QualityAction.status == "PENDING")) or 0
    return {"events": total, "failed": failed, "stale": stale, "pending_actions": pending}

