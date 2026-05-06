# Capacity Planning Methodology (Assignment 6)

## Objective

Evaluate the maximum sustainable load for the containerized microservices stack while keeping reliability SLO guardrails.

## Workload Scenario

- Tool: `k6`
- Scenario file: `scripts/capacity/k6-order-load.js`
- Traffic profile:
  - ramp to 10 VUs (2m)
  - ramp to 30 VUs (3m)
  - ramp to 60 VUs (3m)
  - ramp to 100 VUs (2m)
  - ramp down to 0 VUs (2m)
- Endpoints under load:
  - `GET /api/orders/health`
  - `GET /api/products/categories`
  - `GET /api/orders/`

## Metrics Collected

- Request rate (RPS) from k6 and Prometheus
- Error rate (`http_req_failed`, 5xx rate for `order_service`)
- Latency (`http_req_duration` p95)
- Host/container resource usage (CPU/memory)
- Restart indicators and service health from Docker

## Thresholds (SRE Guardrails)

- Error rate < `5%`
- p95 latency < `800 ms`
- Host CPU < `85%`
- No restart-loop pattern during test window

## Execution

1. Validate configuration before deployment:
   - `make validate-predeploy`
2. Start stack:
   - `make up-build`
3. Run capacity test:
   - `bash scripts/capacity/run-capacity-test.sh`
4. Review generated report:
   - `docs/capacity-planning-results.md`

## Interpreting Maximum Sustainable Load

The maximum sustainable load is the highest stage where all thresholds stay within limits:

- if p95 or error rate breaches thresholds, previous stage is the sustainable baseline;
- if CPU crosses 85% with rising errors, service is near saturation;
- if DB-related errors increase first, database is the bottleneck and requires optimization/pooling.

## Scaling Strategy Link

If thresholds are violated:

1. Horizontal scale `order-service` first.
2. Increase VM/container resources if saturation persists.
3. Optimize DB access path (indexes, pooling, query review).

## Practical Scaling Proof

- Automated proof script: `scripts/capacity/run-scaling-proof.sh`
- Command: `make scaling-proof`
- Output report: `docs/scaling-proof-report.md`

The proof compares baseline (`order-service=1`) and scaled replicas (`order-service=3` by default) on the same k6 load profile and reports:

- RPS change
- p95 latency change
- error-rate change
- pass/fail versus thresholds
