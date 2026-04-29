# Assignment 5 Report: Terraform Infrastructure Provisioning

## Objective

Provision infrastructure declaratively and reproducibly using Terraform for the containerized microservices platform.

## Implemented Infrastructure

- Cloud VM: AWS EC2 instance (`aws_instance.logistics_vm`)
- Network access via Security Group:
  - TCP `22` (SSH)
  - TCP `80` (HTTP)
  - TCP `3000` (Grafana)
  - TCP `9090` (Prometheus)
- Additional app access:
  - TCP `8080` (API gateway/UI)

## Reproducibility

Infrastructure lifecycle uses standard Terraform workflow:

1. `terraform init`
2. `terraform plan`
3. `terraform apply`

Cleanup:

- `terraform destroy`

## Public IP Output

The configuration exposes:

- `public_ip`
- `public_dns`
- `ssh_command`

## Deployment Automation

Cloud-init (`user_data.sh.tftpl`) prepares host and can auto-start the Docker Compose stack:

- Installs Docker + Git
- Clones repository branch
- Creates `.env` if missing
- Runs `docker compose up -d --build` (when enabled)

## Deliverables Checklist

- [x] `main.tf`
- [x] `variables.tf`
- [x] `outputs.tf`
- [x] `terraform.tfvars`
- [x] Deployment documentation (`docs/deployment-guide.md`)

