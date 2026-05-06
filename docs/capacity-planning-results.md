# Capacity Planning Results

Run the practical load test to generate this file automatically:

```bash
bash scripts/capacity/run-capacity-test.sh
```

The script overwrites this document with:

- measured RPS
- measured error rate
- measured p95 latency
- current Prometheus CPU/error/RPS snapshots
- capacity conclusion against thresholds
- docker stats snapshot

If this placeholder still exists, practical test evidence has not been generated yet.
