import argparse
import asyncio
import json
import statistics
import time
from datetime import datetime, timezone

import httpx


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--concurrency", type=int, default=20)
    args = parser.parse_args()
    semaphore = asyncio.Semaphore(args.concurrency)
    latencies = []

    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30, trust_env=False) as client:
        async def send(i):
            payload = {"event_id": f"BENCH-{time.time_ns()}-{i}", "unit_id": f"PACK-B-{i}", "station_id": "STATION-12", "equipment_id": "TORQUE-TOOL-04", "test_name": "bolt_torque", "value": 42.0, "unit": "Nm", "timestamp": datetime.now(timezone.utc).isoformat(), "source": "benchmark"}
            async with semaphore:
                start = time.perf_counter()
                response = await client.post("/api/events", json=payload)
                latencies.append((time.perf_counter() - start) * 1000)
                return response.status_code
        started = time.perf_counter()
        statuses = await asyncio.gather(*(send(i) for i in range(args.count)))
        duration = time.perf_counter() - started
    ordered = sorted(latencies)
    p95 = ordered[max(0, int(len(ordered) * .95) - 1)]
    print(json.dumps({"requests": args.count, "successes": sum(s == 200 for s in statuses), "seconds": round(duration, 3), "throughput_rps": round(args.count / duration, 2), "mean_ms": round(statistics.mean(latencies), 2), "p50_ms": round(statistics.median(latencies), 2), "p95_ms": round(p95, 2)}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
