/**
 * CloudWatch monitoring and alarms
 * - SNS topic for alarm notifications
 * - Alarms for Lambda errors, RDS CPU, Redis memory, etc.
 */

# SNS Topic for CloudWatch alarms
resource "aws_sns_topic" "alarms" {
  name = "${var.project_name}-alarms"

  tags = {
    Name = "${var.project_name}-alarms"
  }
}

# SNS Topic Subscription (Email)
resource "aws_sns_topic_subscription" "alarms_email" {
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# Lambda Error Rate Alarm - Trading Loop
resource "aws_cloudwatch_metric_alarm" "trading_loop_errors" {
  alarm_name          = "${var.project_name}-trading-loop-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Trading loop Lambda error count exceeds threshold"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    FunctionName = aws_lambda_function.trading_loop.function_name
  }

  tags = {
    Name = "${var.project_name}-trading-loop-errors"
  }
}

# Lambda Error Rate Alarm - Settlement
resource "aws_cloudwatch_metric_alarm" "settlement_errors" {
  alarm_name          = "${var.project_name}-settlement-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Settlement Lambda error detected"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    FunctionName = aws_lambda_function.settlement.function_name
  }

  tags = {
    Name = "${var.project_name}-settlement-errors"
  }
}

# Lambda Duration Alarm - Trading Loop
resource "aws_cloudwatch_metric_alarm" "trading_loop_duration" {
  alarm_name          = "${var.project_name}-trading-loop-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300 # 5 minutes
  statistic           = "Average"
  threshold           = 50000 # 50 seconds (approaching 60s timeout)
  alarm_description   = "Trading loop Lambda duration approaching timeout"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    FunctionName = aws_lambda_function.trading_loop.function_name
  }

  tags = {
    Name = "${var.project_name}-trading-loop-duration"
  }
}

# RDS CPU Utilization Alarm
resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${var.project_name}-rds-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300 # 5 minutes
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "RDS CPU utilization exceeds 80%"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = {
    Name = "${var.project_name}-rds-cpu-high"
  }
}

# RDS Free Storage Space Alarm
resource "aws_cloudwatch_metric_alarm" "rds_storage" {
  alarm_name          = "${var.project_name}-rds-storage-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300 # 5 minutes
  statistic           = "Average"
  threshold           = 2147483648 # 2GB in bytes
  alarm_description   = "RDS free storage space below 2GB"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = {
    Name = "${var.project_name}-rds-storage-low"
  }
}

# RDS Database Connections Alarm
resource "aws_cloudwatch_metric_alarm" "rds_connections" {
  alarm_name          = "${var.project_name}-rds-connections-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 300 # 5 minutes
  statistic           = "Average"
  threshold           = 80 # 80% of max_connections (100)
  alarm_description   = "RDS database connections approaching limit"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = {
    Name = "${var.project_name}-rds-connections-high"
  }
}

# ElastiCache CPU Utilization Alarm
resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  alarm_name          = "${var.project_name}-redis-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = 300 # 5 minutes
  statistic           = "Average"
  threshold           = 75
  alarm_description   = "Redis CPU utilization exceeds 75%"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    CacheClusterId = "${aws_elasticache_replication_group.main.replication_group_id}-001"
  }

  tags = {
    Name = "${var.project_name}-redis-cpu-high"
  }
}

# ElastiCache Memory Utilization Alarm
resource "aws_cloudwatch_metric_alarm" "redis_memory" {
  alarm_name          = "${var.project_name}-redis-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = 300 # 5 minutes
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Redis memory usage exceeds 80%"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    CacheClusterId = "${aws_elasticache_replication_group.main.replication_group_id}-001"
  }

  tags = {
    Name = "${var.project_name}-redis-memory-high"
  }
}

# EC2 Dashboard Instance Status Check Alarm
resource "aws_cloudwatch_metric_alarm" "dashboard_status_check" {
  alarm_name          = "${var.project_name}-dashboard-status-check-failed"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = 60 # 1 minute
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Dashboard EC2 instance status check failed"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    InstanceId = aws_instance.dashboard.id
  }

  tags = {
    Name = "${var.project_name}-dashboard-status-check-failed"
  }
}

# EC2 Dashboard CPU Utilization Alarm
resource "aws_cloudwatch_metric_alarm" "dashboard_cpu" {
  alarm_name          = "${var.project_name}-dashboard-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300 # 5 minutes
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Dashboard EC2 CPU utilization exceeds 80%"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    InstanceId = aws_instance.dashboard.id
  }

  tags = {
    Name = "${var.project_name}-dashboard-cpu-high"
  }
}

# NAT Gateway PacketsDropCount Alarm
resource "aws_cloudwatch_metric_alarm" "nat_gateway_packets_drop" {
  alarm_name          = "${var.project_name}-nat-gateway-packets-drop"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "PacketsDropCount"
  namespace           = "AWS/NATGateway"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 1000
  alarm_description   = "NAT Gateway dropping packets"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    NatGatewayId = aws_nat_gateway.main.id
  }

  tags = {
    Name = "${var.project_name}-nat-gateway-packets-drop"
  }
}

# Lambda Throttles Alarm - Trading Loop
resource "aws_cloudwatch_metric_alarm" "trading_loop_throttles" {
  alarm_name          = "${var.project_name}-trading-loop-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = 60 # 1 minute
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Trading loop Lambda is being throttled"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    FunctionName = aws_lambda_function.trading_loop.function_name
  }

  tags = {
    Name = "${var.project_name}-trading-loop-throttles"
  }
}

# Composite Alarm - Critical System Health
resource "aws_cloudwatch_composite_alarm" "system_health" {
  alarm_name          = "${var.project_name}-system-health-critical"
  alarm_description   = "Critical system health issues detected"
  actions_enabled     = true
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]

  alarm_rule = "ALARM(${aws_cloudwatch_metric_alarm.trading_loop_errors.alarm_name}) OR ALARM(${aws_cloudwatch_metric_alarm.rds_cpu.alarm_name}) OR ALARM(${aws_cloudwatch_metric_alarm.dashboard_status_check.alarm_name})"

  tags = {
    Name = "${var.project_name}-system-health-critical"
  }
}
