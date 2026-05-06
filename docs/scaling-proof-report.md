# Scaling Proof Report

Generate this report automatically:

```bash
make scaling-proof
```

The script executes:

1. baseline load test with `order-service=1`
2. horizontal scaling to multiple replicas
3. repeated load test with the same profile
4. comparison of RPS, p95 latency, and error rate

If this placeholder exists, scaling proof has not been generated yet.
