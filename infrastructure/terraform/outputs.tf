/**
 * Terraform outputs - important resource information
 */

# VPC Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "nat_gateway_ip" {
  description = "NAT Gateway public IP"
  value       = aws_eip.nat.public_ip
}

# RDS Outputs
output "rds_endpoint" {
  description = "RDS endpoint address"
  value       = aws_db_instance.main.endpoint
}

output "rds_instance_id" {
  description = "RDS instance identifier"
  value       = aws_db_instance.main.id
}

output "rds_database_name" {
  description = "RDS database name"
  value       = aws_db_instance.main.db_name
}

# ElastiCache Outputs
output "redis_endpoint" {
  description = "Redis primary endpoint address"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "redis_port" {
  description = "Redis port"
  value       = 6379
}

# Lambda Outputs
output "trading_loop_function_name" {
  description = "Trading loop Lambda function name"
  value       = aws_lambda_function.trading_loop.function_name
}

output "trading_loop_function_arn" {
  description = "Trading loop Lambda function ARN"
  value       = aws_lambda_function.trading_loop.arn
}

output "trading_loop_function_url" {
  description = "Trading loop Lambda function URL (manual invocation)"
  value       = aws_lambda_function_url.trading_loop.function_url
}

output "settlement_function_name" {
  description = "Settlement Lambda function name"
  value       = aws_lambda_function.settlement.function_name
}

output "settlement_function_arn" {
  description = "Settlement Lambda function ARN"
  value       = aws_lambda_function.settlement.arn
}

output "settlement_function_url" {
  description = "Settlement Lambda function URL (manual invocation)"
  value       = aws_lambda_function_url.settlement.function_url
}

# EC2 Dashboard Outputs
output "dashboard_public_ip" {
  description = "Dashboard EC2 public IP (Elastic IP)"
  value       = aws_eip.dashboard.public_ip
}

output "dashboard_url" {
  description = "Dashboard URL"
  value       = "http://${aws_eip.dashboard.public_ip}:${var.dashboard_port}"
}

output "dashboard_instance_id" {
  description = "Dashboard EC2 instance ID"
  value       = aws_instance.dashboard.id
}

# Security Group Outputs
output "dashboard_security_group_id" {
  description = "Dashboard security group ID"
  value       = aws_security_group.dashboard.id
}

output "rds_security_group_id" {
  description = "RDS security group ID"
  value       = aws_security_group.rds.id
}

output "redis_security_group_id" {
  description = "Redis security group ID"
  value       = aws_security_group.redis.id
}

output "lambda_security_group_id" {
  description = "Lambda security group ID"
  value       = aws_security_group.lambda.id
}

# CloudWatch Outputs
output "sns_alarm_topic_arn" {
  description = "SNS topic ARN for CloudWatch alarms"
  value       = aws_sns_topic.alarms.arn
}

output "trading_loop_log_group" {
  description = "Trading loop Lambda log group name"
  value       = aws_cloudwatch_log_group.trading_loop.name
}

output "settlement_log_group" {
  description = "Settlement Lambda log group name"
  value       = aws_cloudwatch_log_group.settlement.name
}

output "dashboard_log_group" {
  description = "Dashboard EC2 log group name"
  value       = aws_cloudwatch_log_group.dashboard.name
}

# EventBridge Outputs
output "trading_loop_schedule" {
  description = "Trading loop EventBridge schedule expression"
  value       = aws_cloudwatch_event_rule.trading_loop.schedule_expression
}

output "settlement_schedule" {
  description = "Settlement EventBridge schedule expression"
  value       = aws_cloudwatch_event_rule.settlement.schedule_expression
}

# Cost Estimation
output "estimated_monthly_cost" {
  description = "Estimated monthly AWS cost (USD)"
  value = {
    rds           = "~$15"
    elasticache   = "~$12"
    ec2_dashboard = "~$8"
    nat_gateway   = "~$5"
    secrets       = "~$2"
    total         = "~$42"
    note          = "Estimates based on US East region, single AZ deployment"
  }
}

# Connection Instructions
output "connection_info" {
  description = "Instructions for connecting to deployed resources"
  value = {
    dashboard = "Access dashboard at: http://${aws_eip.dashboard.public_ip}:${var.dashboard_port}"
    ssh       = length(var.ssh_allowed_cidr) > 0 ? "SSH: ssh ec2-user@${aws_eip.dashboard.public_ip}" : "SSH access disabled (no allowed CIDRs configured)"
    rds       = "RDS connection details stored in Secrets Manager: ${aws_secretsmanager_secret.rds_password.name}"
    redis     = "Redis endpoint: ${aws_elasticache_replication_group.main.primary_endpoint_address}:6379"
    lambda    = "Lambda functions invoke via EventBridge schedules or function URLs"
  }
}

# Deployment Checklist
output "deployment_checklist" {
  description = "Post-deployment tasks"
  value = {
    step_1 = "Confirm SNS email subscription (check email: ${var.alarm_email})"
    step_2 = "Deploy application code to EC2 instance"
    step_3 = "Run Alembic migrations on RDS: alembic upgrade head"
    step_4 = "Upload Lambda deployment packages (trading_loop.zip, settlement.zip, layer.zip)"
    step_5 = "Start Streamlit dashboard: systemctl start trading-dashboard"
    step_6 = "Verify Lambda function URLs work (requires AWS IAM authentication)"
    step_7 = "Test EventBridge rules trigger functions"
    step_8 = "Monitor CloudWatch dashboards and alarms"
    step_9 = "Review estimated costs in AWS Cost Explorer after 24 hours"
  }
}
