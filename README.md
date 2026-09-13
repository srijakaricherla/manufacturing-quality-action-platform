# Manufacturing Quality Action Platform

A production-style portfolio project for real-time manufacturing quality decisions. It receives equipment and inspection events, validates them, applies versioned quality rules, stores complete unit traceability, and creates reliable hold/retest/alert actions.

## What it demonstrates

- Python/FastAPI services and documented REST APIs
- Kafka-compatible event ingestion with Redpanda
- PostgreSQL data modeling and unit traceability
- Configurable, versioned quality rules
- Idempotent processing using a unique `event_id`
- Out-of-order event handling
- Transactional creation of quality events and actions
- Retriable downstream actions with stable action IDs
- Prometheus metrics, automated tests, simulation, and benchmarking

## Architecture

`Simulator -> Kafka/REST -> Quality processor -> PostgreSQL -> Action worker -> Dashboard/API`

The event record and required action are committed in the same database transaction. Kafka offsets are committed only after durable processing. Replayed messages are identified by `event_id`, and a deterministic `action_id` prevents duplicate business actions.

## Run the complete stack

1. Install Docker Desktop.
2. From this directory run:

   ```bash
   docker compose up --build
   ```

3. Open:

   - Dashboard: http://localhost:8000
   - API documentation: http://localhost:8000/docs
   - Prometheus: http://localhost:9090

4. Generate REST events:

   ```bash
   python simulator.py --mode api --count 1000 --duplicates 100 --fail-rate 0.1
   ```

5. Generate Kafka events:

   ```bash
   python simulator.py --mode kafka --count 1000 --duplicates 100 --fail-rate 0.1
   ```

6. Measure API performance:

   ```bash
   python scripts/benchmark.py --count 1000 --concurrency 20
   ```

See `DEMO_RESULTS.md` for an initial verified local run and its limitations.

## Event contract

```json
{
  "event_id": "EVT-1001",
  "unit_id": "PACK-501",
  "station_id": "STATION-12",
  "equipment_id": "TORQUE-TOOL-04",
  "test_name": "bolt_torque",
  "value": 48.0,
  "unit": "Nm",
  "timestamp": "2026-09-12T14:30:00Z",
  "source": "equipment_simulator"
}
```

## Verify behavior

```bash
pytest -q
```

The tests verify inclusive rule boundaries, exactly one action for duplicate delivery, safe handling of out-of-order failures, and rejection when no active rule exists.

## Produce honest results

Run the benchmark at least three times under the same configuration. Report the median throughput and p95 latency. For an optimization comparison, record the baseline commit, change one variable, rerun the same workload, and calculate:

`improvement % = (baseline - optimized) / baseline * 100`

Do not describe simulated or benchmarked results as factory production results. Present this as an independent production-style prototype and distinguish it from employer work.

## Interview explanation

“I built an independent manufacturing quality platform that converts equipment and inspection data into traceable actions. It supports configurable rules, duplicate and out-of-order events, atomic event/action persistence, retries, unit history, metrics, and reproducible performance tests. I used simulated data so the complete system can be demonstrated without exposing employer information.”
