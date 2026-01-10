/**
 * Terraform variables for trading system infrastructure
 */

# General variables
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "production"
}

variable "owner_email" {
  description = "Email of infrastructure owner"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "trading-system"
}

# VPC variables
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

# RDS variables
variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "rds_allocated_storage" {
  description = "Allocated storage for RDS in GB"
  type        = number
  default     = 20
}

variable "rds_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "16"
}

variable "rds_database_name" {
  description = "Name of the database to create"
  type        = string
  default     = "trading_db"
}

variable "rds_username" {
  description = "Master username for RDS"
  type        = string
  default     = "trading_admin"
  sensitive   = true
}

variable "rds_backup_retention_days" {
  description = "Number of days to retain RDS backups"
  type        = number
  default     = 7
}

variable "rds_multi_az" {
  description = "Enable multi-AZ deployment for RDS"
  type        = bool
  default     = false
}

# ElastiCache variables
variable "elasticache_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "elasticache_engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.0"
}

variable "elasticache_num_cache_nodes" {
  description = "Number of cache nodes"
  type        = number
  default     = 1
}

# Lambda variables
variable "lambda_runtime" {
  description = "Lambda runtime for Python functions"
  type        = string
  default     = "python3.11"
}

variable "lambda_trading_loop_memory" {
  description = "Memory allocation for trading loop Lambda (MB)"
  type        = number
  default     = 512
}

variable "lambda_trading_loop_timeout" {
  description = "Timeout for trading loop Lambda (seconds)"
  type        = number
  default     = 60
}

variable "lambda_settlement_memory" {
  description = "Memory allocation for settlement Lambda (MB)"
  type        = number
  default     = 256
}

variable "lambda_settlement_timeout" {
  description = "Timeout for settlement Lambda (seconds)"
  type        = number
  default     = 30
}

variable "trading_loop_schedule" {
  description = "EventBridge cron schedule for trading loop (market hours only)"
  type        = string
  default     = "cron(*/1 9-16 ? * MON-FRI *)" # Every 1 minute, 9 AM - 4 PM ET, Mon-Fri
}

variable "settlement_schedule" {
  description = "EventBridge cron schedule for settlement processing"
  type        = string
  default     = "cron(0 16 ? * MON-FRI *)" # 4 PM ET, Mon-Fri
}

# EC2 Dashboard variables
variable "ec2_instance_type" {
  description = "EC2 instance type for Streamlit dashboard"
  type        = string
  default     = "t3.micro"
}

variable "ec2_ami_owner" {
  description = "AMI owner for Amazon Linux 2023"
  type        = string
  default     = "amazon"
}

variable "ec2_ami_name_filter" {
  description = "AMI name filter for Amazon Linux 2023"
  type        = string
  default     = "al2023-ami-*-x86_64"
}

variable "ec2_volume_size" {
  description = "Root volume size for EC2 instance (GB)"
  type        = number
  default     = 30
}

variable "dashboard_port" {
  description = "Port for Streamlit dashboard"
  type        = number
  default     = 8501
}

variable "ssh_allowed_cidr" {
  description = "CIDR blocks allowed to SSH to dashboard EC2 (empty list = no SSH access)"
  type        = list(string)
  default     = [] # Set to your IP for SSH access, e.g., ["YOUR_IP/32"]
}

# Secrets variables (values should be in tfvars file or environment variables)
variable "alpaca_api_key" {
  description = "Alpaca API key"
  type        = string
  sensitive   = true
}

variable "alpaca_api_secret" {
  description = "Alpaca API secret"
  type        = string
  sensitive   = true
}

variable "discord_webhook_url" {
  description = "Discord webhook URL for notifications"
  type        = string
  sensitive   = true
  default     = ""
}

# CloudWatch variables
variable "cloudwatch_log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 14
}

variable "alarm_email" {
  description = "Email address for CloudWatch alarms"
  type        = string
}

variable "alert_email" {
  description = "Email address for budget alerts (same as alarm_email)"
  type        = string
  default     = ""
}

# Tags
variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
