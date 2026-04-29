# Incident Simulation Plan

## Scenario

Simulate a production incident where `order-service` becomes unavailable and users cannot load "My orders" or create new orders.

## Goal

- Validate alerting in Prometheus.
- Practice response flow (detect, mitigate, recover, verify).
- Produce postmortem artifacts.

## Preconditions

- Stack is running (`docker compose up -d`).
- Prometheus target `order_service` is `UP`.
- Frontend available via `http://localhost:8080`.

## Simulation Steps

1. **Baseline check**
   - `make health`
   - Verify `order-service` health endpoint returns `200`.
2. **Inject incident**
   - `docker compose stop order-service`
3. **Observe impact**
   - UI: "My orders" and order creation fail.
   - Prometheus: alert `BackendDownCritical` fires for `order_service`.
4. **Mitigation**
   - `docker compose start order-service`
   - If needed: `docker compose restart gateway`
5. **Recovery verification**
   - `make health`
   - Confirm alerts resolved.
   - Validate order list and order creation from UI.

## Evidence to Capture

- Screenshot: failing frontend request.
- Screenshot: Prometheus alert firing.
- Screenshot: service recovered and healthy.
- Logs: `docker compose logs order-service --tail 200`.

