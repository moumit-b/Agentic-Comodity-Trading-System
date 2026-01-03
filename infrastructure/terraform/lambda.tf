/**
 * Lambda functions configuration
 * - Trading Loop Lambda: Runs every 1 minute during market hours
 * - Settlement Lambda: Runs daily at market close
 */

# IAM Role for Lambda
resource "aws_iam_role" "lambda" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-lambda-role"
  }
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Attach VPC execution policy
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Custom policy for Secrets Manager access
resource "aws_iam_policy" "lambda_secrets" {
  name        = "${var.project_name}-lambda-secrets-policy"
  description = "Allow Lambda to read Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.alpaca.arn,
          aws_secretsmanager_secret.rds_password.arn,
          aws_secretsmanager_secret.redis.arn,
          aws_secretsmanager_secret.discord.arn
        ]
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-lambda-secrets-policy"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_secrets" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.lambda_secrets.arn
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "trading_loop" {
  name              = "/aws/lambda/${var.project_name}-trading-loop"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = {
    Name = "${var.project_name}-trading-loop-logs"
  }
}

resource "aws_cloudwatch_log_group" "settlement" {
  name              = "/aws/lambda/${var.project_name}-settlement"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = {
    Name = "${var.project_name}-settlement-logs"
  }
}

# Lambda Layer for dependencies (shared between functions)
# NOTE: This assumes you've built a layer zip with all dependencies
# Build with: cd infrastructure/lambda && pip install -r requirements.txt -t python/lib/python3.11/site-packages/
resource "aws_lambda_layer_version" "dependencies" {
  filename            = "${path.module}/../lambda/layer.zip"
  layer_name          = "${var.project_name}-dependencies"
  compatible_runtimes = [var.lambda_runtime]
  source_code_hash    = fileexists("${path.module}/../lambda/layer.zip") ? filebase64sha256("${path.module}/../lambda/layer.zip") : null

  description = "Trading system dependencies (SQLAlchemy, Redis, Alpaca SDK, etc.)"

  lifecycle {
    create_before_destroy = true
  }
}

# Trading Loop Lambda Function
resource "aws_lambda_function" "trading_loop" {
  filename      = "${path.module}/../lambda/trading_loop.zip"
  function_name = "${var.project_name}-trading-loop"
  role          = aws_iam_role.lambda.arn
  handler       = "handler.lambda_handler"
  runtime       = var.lambda_runtime
  timeout       = var.lambda_trading_loop_timeout
  memory_size   = var.lambda_trading_loop_memory

  source_code_hash = fileexists("${path.module}/../lambda/trading_loop.zip") ? filebase64sha256("${path.module}/../lambda/trading_loop.zip") : null

  layers = [aws_lambda_layer_version.dependencies.arn]

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      ENVIRONMENT            = var.environment
      SECRETS_MANAGER_REGION = var.aws_region
      ALPACA_SECRET_NAME     = aws_secretsmanager_secret.alpaca.name
      DATABASE_SECRET_NAME   = aws_secretsmanager_secret.rds_password.name
      REDIS_SECRET_NAME      = aws_secretsmanager_secret.redis.name
      DISCORD_SECRET_NAME    = aws_secretsmanager_secret.discord.name
    }
  }

  tags = {
    Name      = "${var.project_name}-trading-loop"
    Component = "Trading"
  }

  depends_on = [
    aws_cloudwatch_log_group.trading_loop,
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy_attachment.lambda_vpc,
    aws_iam_role_policy_attachment.lambda_secrets,
  ]
}

# Settlement Lambda Function
resource "aws_lambda_function" "settlement" {
  filename      = "${path.module}/../lambda/settlement.zip"
  function_name = "${var.project_name}-settlement"
  role          = aws_iam_role.lambda.arn
  handler       = "handler.lambda_handler"
  runtime       = var.lambda_runtime
  timeout       = var.lambda_settlement_timeout
  memory_size   = var.lambda_settlement_memory

  source_code_hash = fileexists("${path.module}/../lambda/settlement.zip") ? filebase64sha256("${path.module}/../lambda/settlement.zip") : null

  layers = [aws_lambda_layer_version.dependencies.arn]

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      ENVIRONMENT            = var.environment
      SECRETS_MANAGER_REGION = var.aws_region
      ALPACA_SECRET_NAME     = aws_secretsmanager_secret.alpaca.name
      DATABASE_SECRET_NAME   = aws_secretsmanager_secret.rds_password.name
      REDIS_SECRET_NAME      = aws_secretsmanager_secret.redis.name
      DISCORD_SECRET_NAME    = aws_secretsmanager_secret.discord.name
    }
  }

  tags = {
    Name      = "${var.project_name}-settlement"
    Component = "Trading"
  }

  depends_on = [
    aws_cloudwatch_log_group.settlement,
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy_attachment.lambda_vpc,
    aws_iam_role_policy_attachment.lambda_secrets,
  ]
}

# EventBridge Rule for Trading Loop (every 1 minute, market hours only)
resource "aws_cloudwatch_event_rule" "trading_loop" {
  name                = "${var.project_name}-trading-loop-schedule"
  description         = "Trigger trading loop every minute during market hours"
  schedule_expression = var.trading_loop_schedule

  tags = {
    Name = "${var.project_name}-trading-loop-schedule"
  }
}

resource "aws_cloudwatch_event_target" "trading_loop" {
  rule      = aws_cloudwatch_event_rule.trading_loop.name
  target_id = "TradingLoopLambda"
  arn       = aws_lambda_function.trading_loop.arn
}

resource "aws_lambda_permission" "trading_loop_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.trading_loop.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.trading_loop.arn
}

# EventBridge Rule for Settlement (daily at market close)
resource "aws_cloudwatch_event_rule" "settlement" {
  name                = "${var.project_name}-settlement-schedule"
  description         = "Trigger settlement processing at market close"
  schedule_expression = var.settlement_schedule

  tags = {
    Name = "${var.project_name}-settlement-schedule"
  }
}

resource "aws_cloudwatch_event_target" "settlement" {
  rule      = aws_cloudwatch_event_rule.settlement.name
  target_id = "SettlementLambda"
  arn       = aws_lambda_function.settlement.arn
}

resource "aws_lambda_permission" "settlement_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.settlement.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.settlement.arn
}

# Lambda Function URLs (optional - for manual invocation)
resource "aws_lambda_function_url" "trading_loop" {
  function_name      = aws_lambda_function.trading_loop.function_name
  authorization_type = "AWS_IAM" # Require IAM authentication

  cors {
    allow_origins     = ["*"]
    allow_methods     = ["POST"]
    allow_headers     = ["*"]
    expose_headers    = ["*"]
    max_age           = 86400
  }
}

resource "aws_lambda_function_url" "settlement" {
  function_name      = aws_lambda_function.settlement.function_name
  authorization_type = "AWS_IAM" # Require IAM authentication

  cors {
    allow_origins     = ["*"]
    allow_methods     = ["POST"]
    allow_headers     = ["*"]
    expose_headers    = ["*"]
    max_age           = 86400
  }
}
