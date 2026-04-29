# Logistics SRE Assignment Baseline

This repository contains a containerized logistics platform prepared for an SRE/IaC assignment.

## Stage 0 Deliverables

### Baseline freeze

- Working branch for assignment: `assignment/baseline-microservices`
- Scope frozen around:
  - microservice split
  - gateway routing
  - monitoring continuity
  - documentation and acceptance checklist

### Plan of work + Definition of Done

#### Work plan

1. Establish baseline and documentation.
2. Split backend responsibilities into separate services.
3. Introduce API gateway and stable request routing.
4. Keep monitoring stack operational.
5. Validate startup and endpoint health.

#### Definition of Done

- All services run with `docker compose up --build`.
- API gateway routes all required paths.
- Frontend is served as static app behind gateway.
- Functional and non-functional checklists are documented.
- Demo script and evidence checklist are documented.

## Architecture

### Components

- `frontend` (React static build served by Nginx)
- `gateway` (Nginx reverse proxy)
- `auth-service` (registration/login/token)
- `user-service` (profile/users)
- `product-service` (catalog/categories)
- `order-service` (create/list/update orders, orchestrates product+ml)
- `chat-service` (MVP chat messages)
- `ml_service` (risk prediction model API)
- `logistics_db` (PostgreSQL)
- `prometheus`, `grafana`, `node_exporter` (observability)

### Request flow

1. Client requests arrive at `gateway` (`:8080`).
2. Gateway forwards:
   - `/api/auth/*` -> `auth-service`
   - `/api/users/*` -> `user-service`
   - `/api/products/*` -> `product-service`
   - `/api/orders/*` -> `order-service`
   - `/api/chat/*` -> `chat-service`
   - `/api/ml/*`, `/api/analytics/*` -> `order-service` compatibility endpoints
   - `/` -> `frontend`
3. `order-service` performs internal HTTP calls:
   - `order-service` -> `product-service` (category validation)
   - `order-service` -> `ml_service` (risk prediction)
4. Each service propagates `X-Request-ID`.

## Services and Ports

- Gateway: `8080`
- Frontend direct (optional): `3002`
- Auth: `8002`
- Product: `8003`
- User: `8004`
- Order: `8005`
- Chat: `8006`
- ML service: `8001`
- PostgreSQL: `5433`
- Prometheus: `9090`
- Grafana: `3001`
- Node exporter: `9100`

## Run

### Prerequisites

- Docker + Docker Compose plugin
- `.env` file in repository root

### Environment example

Use `.env.example` as a base and ensure:

- `DATABASE_URL=postgresql://user:password@logistics_db:5432/logistics_risk_db`
- `SECRET_KEY=<your_secret>`
- `ALGORITHM=HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES=60`

### Start

```bash
make up-build
```

### Quick health checks

```bash
curl http://localhost:8080/api/auth/health
curl http://localhost:8080/api/users/health
curl http://localhost:8080/api/products/health
curl http://localhost:8080/api/orders/health
curl http://localhost:8080/api/chat/health
```

## Monitoring

- Prometheus target config: `prometheus.yml`
- Alerting rules: `alert_rules.yml`
- Dashboards: Grafana at `http://localhost:3001`

Implemented metrics coverage:

- all new microservices expose `/metrics`
- ML service exposes `/metrics`
- node exporter metrics available for host visibility

## Assignment Compliance Checklist

### Functional requirements

- [x] Web interface for user interaction
- [x] Authentication and role-based authorization
- [x] Product retrieval (`/api/products`)
- [x] Transaction operation: create order (`/api/orders`)
- [x] Inter-service communication over HTTP
- [x] Metrics exposure for monitoring
- [x] Failure detection via Prometheus alert rules

### Non-functional requirements

- [x] Modular decomposition into microservices
- [x] Fault isolation by separated service processes/containers
- [x] Observability via Prometheus + Grafana
- [x] Automated infrastructure provisioning with Terraform
- [x] Containerized execution with Docker Compose
- [x] Reproducible startup via compose and env file

## Demo Script (Acceptance)

1. Start stack: `docker compose up --build`
2. Open frontend: `http://localhost:8080`
3. Register/login through auth endpoints from UI.
4. Load product categories and create order.
5. Confirm order was scored via ML and persisted.
6. Open Prometheus and verify targets are `UP`.
7. Open Grafana and verify dashboard panels show metrics.
8. Trigger controlled failure and show alert firing using `docs/incident-simulation.md`.

## Evidence Checklist

Collect artifacts for submission:

- [ ] Screenshot: all containers healthy
- [ ] Screenshot: gateway routes working
- [ ] Screenshot: frontend login + order creation
- [ ] Screenshot: Prometheus targets page
- [ ] Screenshot: Grafana dashboard
- [ ] Logs: service startup logs per component
- [ ] Logs: sample request trace with `X-Request-ID`
- [x] Document template: incident timeline/runbook
- [x] Document template: postmortem

## Notes

- Legacy monolith code remains in `app/` and is reused by service modules for models/security utilities to reduce migration risk in Stage 1.
- Stage 2+ should extract shared libraries and migrate Terraform from local compose automation to real cloud modules (VPC/VM/K8s).

## Terraform (Assignment 5)

Terraform provisions cloud infrastructure for the assignment:

- VM instance (AWS EC2)
- Security group rules for `22`, `80`, `3000`, `9090` (and `8080` for app gateway)
- Public IP/DNS outputs

Core files:

- `terraform/main.tf`
- `terraform/variables.tf`
- `terraform/outputs.tf`
- `terraform/terraform.tfvars`

Run:

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Detailed steps: `docs/deployment-guide.md`.

## Incident Response Artifacts

- Simulation scenario: `docs/incident-simulation.md`
- Response runbook: `docs/incident-response-runbook.md`
- Postmortem template: `docs/postmortem-template.md`
- Assignment 5 report: `docs/assignment-5-report.md`

## Docker Stack (Swarm)

A swarm-compatible manifest is included: `docker-stack.yml`.

```bash
docker swarm init
docker stack deploy -c docker-stack.yml logistics
```

## Fast Update Workflow (no down/up each change)

You do **not** need `docker compose down` every time.

- Start once: `make up-build`
- For code-only updates in one service:
  - auth: `make rebuild-auth`
  - order: `make rebuild-order`
  - frontend: `make rebuild-frontend`
- Check status: `make ps`
- Health: `make health`

`docker compose down` is needed only when you want to fully stop and clean up.
