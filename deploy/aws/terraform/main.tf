# Terraform configuration for Trading Scanner on AWS
# Usage:
#   cd deploy/aws/terraform
#   terraform init
#   terraform apply

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  default = "us-east-1"
}

variable "instance_type" {
  default = "t3.micro"  # Free tier eligible
}

variable "key_name" {
  description = "Name of existing EC2 key pair"
  type        = string
}

variable "your_ip" {
  description = "Your IP address for SSH access (e.g., 1.2.3.4/32)"
  type        = string
}

# Data sources
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]  # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-*-24.04-amd64-server-*"]
  }
}

# Security Group
resource "aws_security_group" "scanner" {
  name        = "trading-scanner-sg"
  description = "Security group for trading scanner"

  # SSH access from your IP only
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.your_ip]
  }

  # All outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "trading-scanner"
  }
}

# EC2 Instance
resource "aws_instance" "scanner" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  key_name      = var.key_name

  vpc_security_group_ids = [aws_security_group.scanner.id]

  root_block_device {
    volume_size = 8
    volume_type = "gp3"
  }

  user_data = <<-EOF
    #!/bin/bash
    curl -sSL https://raw.githubusercontent.com/hiddingtrojans/trading-lab/main/deploy/aws/setup.sh | bash
  EOF

  tags = {
    Name = "trading-scanner"
  }
}

# Outputs
output "instance_ip" {
  value = aws_instance.scanner.public_ip
}

output "ssh_command" {
  value = "ssh -i ${var.key_name}.pem ubuntu@${aws_instance.scanner.public_ip}"
}

