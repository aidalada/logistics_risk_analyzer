variable "aws_region" {
  description = "AWS region for provisioning"
  type        = string
  default     = "eu-central-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small"
}

variable "key_pair_name" {
  description = "Existing AWS key pair name for SSH access (optional)"
  type        = string
  default     = ""
}

variable "project_name" {
  description = "Name prefix for infrastructure resources"
  type        = string
  default     = "logistics-sre"
}

variable "repo_url" {
  description = "Git repository URL used by cloud-init to deploy app"
  type        = string
}

variable "repo_branch" {
  description = "Repository branch to deploy"
  type        = string
  default     = "main"
}

variable "app_directory" {
  description = "Directory on VM where project will be cloned"
  type        = string
  default     = "/opt/logistics_project"
}

variable "allow_cidr" {
  description = "CIDR allowed to access instance ports"
  type        = string
  default     = "0.0.0.0/0"
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}

variable "create_app_stack" {
  description = "If true, user_data starts docker compose stack automatically"
  type        = bool
  default     = true
}

variable "ssh_port" {
  description = "SSH port"
  type        = number
  default     = 22
}

variable "http_port" {
  description = "HTTP port"
  type        = number
  default     = 80
}

variable "grafana_port" {
  description = "Grafana port"
  type        = number
  default     = 3000
}

variable "prometheus_port" {
  description = "Prometheus port"
  type        = number
  default     = 9090
}

