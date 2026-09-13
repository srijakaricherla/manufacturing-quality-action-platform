# Verified local demonstration

Run date: September 12, 2026

Environment: local FastAPI application with SQLite, using the included simulator and benchmark scripts. These are development-environment results, not factory production results.

## Functional verification

- Automated tests: 4 passed
- Verified inclusive rule boundaries
- Verified duplicate delivery creates exactly one action
- Verified out-of-order failure is retained without changing disposition
- Verified events without an active rule are rejected

## Initial measured run

Simulator configuration:

```bash
python simulator.py --mode api --count 200 --duplicates 20 --fail-rate 0.1 --shuffle
```

- Messages sent: 220
- Unique event IDs generated: 200
- Intentional duplicate messages: 20
- Simulator send rate: 287.04 events/second

Benchmark configuration:

```bash
python scripts/benchmark.py --count 300 --concurrency 10
```

- Successful requests: 300 of 300
- Throughput: 277.53 requests/second
- Mean response time: 34.10 ms
- Median response time: 21.44 ms
- p95 response time: 87.26 ms

These values are one initial measured run. Repeat the same workload at least three times before citing a representative result. PostgreSQL/Docker results will differ from this SQLite development run.
