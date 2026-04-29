data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["137112412989"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}

locals {
  common_tags = merge(
    {
      Project     = var.project_name
      ManagedBy   = "Terraform"
      Environment = "assignment"
    },
    var.tags
  )

  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    repo_url         = var.repo_url
    repo_branch      = var.repo_branch
    app_directory    = var.app_directory
    create_app_stack = var.create_app_stack
  })
}

resource "aws_security_group" "logistics_sre" {
  name        = "${var.project_name}-sg"
  description = "Security group for logistics SRE assignment"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = var.ssh_port
    to_port     = var.ssh_port
    protocol    = "tcp"
    cidr_blocks = [var.allow_cidr]
    description = "SSH"
  }

  ingress {
    from_port   = var.http_port
    to_port     = var.http_port
    protocol    = "tcp"
    cidr_blocks = [var.allow_cidr]
    description = "HTTP"
  }

  ingress {
    from_port   = var.grafana_port
    to_port     = var.grafana_port
    protocol    = "tcp"
    cidr_blocks = [var.allow_cidr]
    description = "Grafana"
  }

  ingress {
    from_port   = var.prometheus_port
    to_port     = var.prometheus_port
    protocol    = "tcp"
    cidr_blocks = [var.allow_cidr]
    description = "Prometheus"
  }

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = [var.allow_cidr]
    description = "Gateway API/UI"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

resource "aws_instance" "logistics_vm" {
  ami                         = data.aws_ami.amazon_linux_2023.id
  instance_type               = var.instance_type
  subnet_id                   = data.aws_subnets.default.ids[0]
  vpc_security_group_ids      = [aws_security_group.logistics_sre.id]
  key_name                    = var.key_pair_name != "" ? var.key_pair_name : null
  associate_public_ip_address = true
  user_data                   = local.user_data

  tags = merge(
    local.common_tags,
    { Name = "${var.project_name}-vm" }
  )
}

