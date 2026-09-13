import argparse
import json
import random
import time
from datetime import datetime, timezone

import httpx
from confluent_kafka import Producer


def event(index: int, fail_rate: float):
    failed = random.random() < fail_rate
    return {
        "event_id": f"EVT-{index:06d}", "unit_id": f"PACK-{index // 2:05d}",
        "station_id": "STATION-12", "equipment_id": "TORQUE-TOOL-04",
        "test_name": "bolt_torque", "value": 48.0 if failed else round(random.uniform(40, 45), 2),
        "unit": "Nm", "timestamp": datetime.now(timezone.utc).isoformat(), "source": "equipment_simulator",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--fail-rate", type=float, default=0.1)
    parser.add_argument("--duplicates", type=int, default=10)
    parser.add_argument("--mode", choices=["api", "kafka"], default="api")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--shuffle", action="store_true")
    args = parser.parse_args()
    random.seed(args.seed)
    events = [event(i, args.fail_rate) for i in range(args.count)]
    events.extend(events[: min(args.duplicates, len(events))])
    if args.shuffle:
        random.shuffle(events)
    started = time.perf_counter()
    if args.mode == "api":
        with httpx.Client(base_url="http://localhost:8000", timeout=30, trust_env=False) as client:
            for item in events:
                response = client.post("/api/events", json=item)
                response.raise_for_status()
    else:
        producer = Producer({"bootstrap.servers": "localhost:19092"})
        for item in events:
            producer.produce("quality-events", key=item["unit_id"], value=json.dumps(item))
        producer.flush()
    duration = time.perf_counter() - started
    print(json.dumps({"sent": len(events), "unique": args.count, "duplicates": min(args.duplicates, args.count), "seconds": round(duration, 3), "events_per_second": round(len(events) / duration, 2)}, indent=2))


if __name__ == "__main__":
    main()
