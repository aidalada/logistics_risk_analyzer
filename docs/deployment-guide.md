# Deployment Guide (Assignment 5)

## Prerequisites

- Terraform >= 1.5
- AWS account with credentials configured (`aws configure`)
- Existing AWS key pair for SSH access

## Terraform Files

- `terraform/main.tf`
- `terraform/variables.tf`
- `terraform/outputs.tf`
- `terraform/terraform.tfvars`

## Configure Variables

Edit `terraform/terraform.tfvars`:

- `key_pair_name` -> your AWS keypair
- `repo_url` -> your repository URL
- `repo_branch` -> branch to deploy
- `aws_region` -> desired region

## Deploy Infrastructure

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

## Expected Result

Terraform provisions:

- 1 EC2 VM
- Security group with inbound ports:
  - `22` (SSH)
  - `80` (HTTP)
  - `3000` (Grafana)
  - `9090` (Prometheus)
- Public IP output

## Verify Outputs

```bash
terraform output public_ip
terraform output ssh_command
```

## Access Services

Using `<PUBLIC_IP>` from Terraform output:

- App/Gateway: `http://<PUBLIC_IP>:8080`
- Grafana: `http://<PUBLIC_IP>:3000`
- Prometheus: `http://<PUBLIC_IP>:9090`

## Destroy

```bash
terraform destroy
```

