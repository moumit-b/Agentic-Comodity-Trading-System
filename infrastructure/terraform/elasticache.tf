/**
 * ElastiCache Redis configuration
 * - Single node for cost optimization
 * - Redis 7.x with persistence enabled
 * - Automatic failover disabled (single node)
 */

# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-redis-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-redis-subnet-group"
  }
}

# ElastiCache Parameter Group
resource "aws_elasticache_parameter_group" "main" {
  name   = "${var.project_name}-redis-params"
  family = "redis7"

  # Memory management
  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru" # Evict least recently used keys when memory is full
  }

  # Timeout
  parameter {
    name  = "timeout"
    value = "300" # Close idle connections after 5 minutes
  }

  tags = {
    Name = "${var.project_name}-redis-params"
  }
}

# ElastiCache Replication Group (single node)
resource "aws_elasticache_replication_group" "main" {
  replication_group_id = "${var.project_name}-redis"
  description          = "Redis cache for trading system"

  # Engine configuration
  engine               = "redis"
  engine_version       = var.elasticache_engine_version
  node_type            = var.elasticache_node_type
  num_cache_clusters   = var.elasticache_num_cache_nodes
  port                 = 6379
  parameter_group_name = aws_elasticache_parameter_group.main.name

  # Network configuration
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  # Snapshot configuration
  snapshot_retention_limit = 5 # Keep 5 daily snapshots
  snapshot_window          = "03:00-05:00" # UTC
  maintenance_window       = "sun:05:00-sun:06:00" # UTC

  # Automatic failover (disabled for single node)
  automatic_failover_enabled = false
  multi_az_enabled           = false

  # At-rest encryption
  at_rest_encryption_enabled = true
  # In-transit encryption
  transit_encryption_enabled = false # Disabled for simplicity (enable in production)

  # Auto minor version upgrade
  auto_minor_version_upgrade = true

  # Log delivery configuration
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_engine_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "engine-log"
  }

  # Notification configuration (optional)
  # notification_topic_arn = aws_sns_topic.elasticache_notifications.arn

  tags = {
    Name       = "${var.project_name}-redis"
    Component  = "Cache"
    CostCenter = "Infrastructure"
  }
}

# CloudWatch Log Group for Redis Slow Log
resource "aws_cloudwatch_log_group" "redis_slow_log" {
  name              = "/aws/elasticache/${var.project_name}-redis/slow-log"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = {
    Name = "${var.project_name}-redis-slow-log"
  }
}

# CloudWatch Log Group for Redis Engine Log
resource "aws_cloudwatch_log_group" "redis_engine_log" {
  name              = "/aws/elasticache/${var.project_name}-redis/engine-log"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = {
    Name = "${var.project_name}-redis-engine-log"
  }
}

# Store Redis connection info in Secrets Manager
resource "aws_secretsmanager_secret" "redis" {
  name                    = "${var.project_name}/redis/connection"
  description             = "ElastiCache Redis connection details"
  recovery_window_in_days = 7

  tags = {
    Name = "${var.project_name}-redis-secret"
  }
}

resource "aws_secretsmanager_secret_version" "redis" {
  secret_id = aws_secretsmanager_secret.redis.id
  secret_string = jsonencode({
    host = aws_elasticache_replication_group.main.primary_endpoint_address
    port = 6379
  })
}
