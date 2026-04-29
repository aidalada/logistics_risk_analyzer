output "instance_id" {
  description = "Provisioned EC2 instance ID"
  value       = aws_instance.logistics_vm.id
}

output "public_ip" {
  description = "Public IP address of the provisioned VM"
  value       = aws_instance.logistics_vm.public_ip
}

output "public_dns" {
  description = "Public DNS name of the provisioned VM"
  value       = aws_instance.logistics_vm.public_dns
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = var.key_pair_name != "" ? "ssh -i <path-to-key>.pem ec2-user@${aws_instance.logistics_vm.public_ip}" : "Set key_pair_name to enable SSH access"
}

