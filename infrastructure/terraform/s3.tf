/**
 * S3 bucket for Lambda deployment packages
 * Used for storing Lambda layers and function code
 */

# S3 bucket for Lambda deployment artifacts
resource "aws_s3_bucket" "lambda_artifacts" {
  bucket = "${var.project_name}-lambda-artifacts-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name      = "${var.project_name}-lambda-artifacts"
    Component = "Lambda"
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "lambda_artifacts" {
  bucket = aws_s3_bucket.lambda_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning
resource "aws_s3_bucket_versioning" "lambda_artifacts" {
  bucket = aws_s3_bucket.lambda_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Lifecycle policy to delete old versions after 30 days
resource "aws_s3_bucket_lifecycle_configuration" "lambda_artifacts" {
  bucket = aws_s3_bucket.lambda_artifacts.id

  rule {
    id     = "delete-old-versions"
    status = "Enabled"

    filter {} # Apply to all objects

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# DEPRECATED: Lambda deployment now uses container images in ECR, not ZIP files in S3
# Keeping S3 resources commented out for reference

# Upload Lambda layer to S3
# resource "aws_s3_object" "lambda_layer" {
#   bucket = aws_s3_bucket.lambda_artifacts.id
#   key    = "layers/dependencies-${filemd5("${path.module}/../lambda/layer.zip")}.zip"
#   source = "${path.module}/../lambda/layer.zip"
#   etag   = filemd5("${path.module}/../lambda/layer.zip")
#
#   tags = {
#     Name = "lambda-dependencies-layer"
#   }
# }

# Upload trading loop function to S3
# resource "aws_s3_object" "trading_loop_function" {
#   bucket = aws_s3_bucket.lambda_artifacts.id
#   key    = "functions/trading_loop-${filemd5("${path.module}/../lambda/trading_loop.zip")}.zip"
#   source = "${path.module}/../lambda/trading_loop.zip"
#   etag   = filemd5("${path.module}/../lambda/trading_loop.zip")
#
#   tags = {
#     Name = "trading-loop-function"
#   }
# }

# Upload settlement function to S3
# resource "aws_s3_object" "settlement_function" {
#   bucket = aws_s3_bucket.lambda_artifacts.id
#   key    = "functions/settlement-${filemd5("${path.module}/../lambda/settlement.zip")}.zip"
#   source = "${path.module}/../lambda/settlement.zip"
#   etag   = filemd5("${path.module}/../lambda/settlement.zip")
#
#   tags = {
#     Name = "settlement-function"
#   }
# }
