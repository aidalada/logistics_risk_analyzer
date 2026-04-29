# Incident Response Runbook

## Severity

- **SEV-2**: Core function degraded (orders unavailable), no data loss.

## Roles

- Incident Commander (IC): coordinates timeline and decisions.
- Ops Engineer: executes mitigation commands.
- Communications: status updates and summary notes.

## Detection

Signals:
- Prometheus alert `BackendDownCritical`.
- Frontend error for orders endpoints.
- Gateway `502` in logs.

## Triage Checklist

1. Confirm scope (`order-service` only or wider outage).
2. Confirm database availability.
3. Check `docker compose ps` status.
4. Check logs:
   - `docker compose logs order-service --tail 200`
   - `docker compose logs gateway --tail 200`

## Mitigation Commands

```bash
docker compose start order-service
docker compose restart gateway
```

If service still unhealthy:

```bash
docker compose up -d --build order-service
docker compose restart gateway
```

## Recovery Validation

```bash
make health
curl -fsS http://localhost:8080/api/orders/health
```

- Validate UI order list and order creation.
- Confirm alert resolved in Prometheus.

## Communication Template

- **Detected:** `<timestamp>`
- **Impact:** `Order API unavailable`
- **Current status:** `<investigating/mitigating/resolved>`
- **Next update:** `<time>`

