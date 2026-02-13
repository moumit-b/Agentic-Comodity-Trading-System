/**
 * AWS Secrets Manager configuration
 * Stores sensitive credentials for:
 * - Alpaca API (trading)
 * - Discord webhook (notifications)
 * - RDS password (managed in rds.tf)
 * - Redis connection (managed in elasticache.tf)
 */

# Alpaca API credentials
resource "aws_secretsmanager_secret" "alpaca" {
  name                    = "${var.project_name}/alpaca/credentials"
  description             = "Alpaca API key and secret for trading"
  recovery_window_in_days = 7

  tags = {
    Name      = "${var.project_name}-alpaca-secret"
    Component = "Trading"
  }
}

resource "aws_secretsmanager_secret_version" "alpaca" {
  secret_id = aws_secretsmanager_secret.alpaca.id
  secret_string = jsonencode({
    api_key    = var.alpaca_api_key
    api_secret = var.alpaca_api_secret
    paper      = true # Hardcoded to paper trading for safety
  })
}

# Discord webhook credentials
resource "aws_secretsmanager_secret" "discord" {
  name                    = "${var.project_name}/discord/webhook"
  description             = "Discord webhook URL for notifications"
  recovery_window_in_days = 7

  tags = {
    Name      = "${var.project_name}-discord-secret"
    Component = "Notifications"
  }
}

resource "aws_secretsmanager_secret_version" "discord" {
  secret_id = aws_secretsmanager_secret.discord.id
  secret_string = jsonencode({
    webhook_url = var.discord_webhook_url != "" ? var.discord_webhook_url : "https://discord.com/api/webhooks/PLACEHOLDER"
  })
}

# LLM API credentials (Phase 2: Groq + Gemini)
resource "aws_secretsmanager_secret" "llm" {
  name                    = "${var.project_name}/llm/credentials"
  description             = "LLM API keys for Groq (primary) and Gemini (fallback)"
  recovery_window_in_days = 7

  tags = {
    Name      = "${var.project_name}-llm-secret"
    Component = "Phase2-GenAI"
  }
}

resource "aws_secretsmanager_secret_version" "llm" {
  secret_id = aws_secretsmanager_secret.llm.id
  secret_string = jsonencode({
    groq_api_key   = var.groq_api_key
    gemini_api_key = var.gemini_api_key
  })
}

# Output secret ARNs for reference
output "secret_arns" {
  description = "ARNs of all secrets"
  value = {
    alpaca   = aws_secretsmanager_secret.alpaca.arn
    discord  = aws_secretsmanager_secret.discord.arn
    database = aws_secretsmanager_secret.rds_password.arn
    redis    = aws_secretsmanager_secret.redis.arn
    llm      = aws_secretsmanager_secret.llm.arn
  }
  sensitive = true
}
