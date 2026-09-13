import json
import random
import signal
import time

from confluent_kafka import Consumer
from sqlalchemy import select

from app.config import settings
from app.db import Base, SessionLocal, engine
from app.models import QualityAction
from app.processor import process_event
from app.schemas import EventIn

running = True


def stop(*_):
    global running
    running = False


def dispatch_pending():
    with SessionLocal() as db:
        actions = db.scalars(select(QualityAction).where(QualityAction.status.in_(["PENDING", "RETRY"])).limit(20)).all()
        for action in actions:
            action.attempts += 1
            if random.random() < settings.action_failure_rate:
                action.status = "RETRY"
                action.last_error = "simulated downstream timeout"
            else:
                action.status = "CONFIRMED"
                action.last_error = None
        db.commit()


def main():
    Base.metadata.create_all(engine)
    consumer = Consumer({
        "bootstrap.servers": settings.kafka_bootstrap_servers,
        "group.id": "quality-action-worker",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    consumer.subscribe([settings.kafka_topic])
    while running:
        message = consumer.poll(1.0)
        if message and not message.error():
            try:
                payload = EventIn.model_validate(json.loads(message.value()))
                with SessionLocal() as db:
                    result = process_event(db, payload)
                if result.status != "REJECTED":
                    consumer.commit(message=message, asynchronous=False)
            except Exception as exc:
                print(f"event rejected: {exc}", flush=True)
        dispatch_pending()
        time.sleep(0.1)
    consumer.close()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    main()

