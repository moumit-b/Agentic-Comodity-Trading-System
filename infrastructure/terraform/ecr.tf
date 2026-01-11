/**
 * ECR repository for Lambda container images
 */

resource "aws_ecr_repository" "trading_lambda" {
  name                 = "${var.project_name}-lambda"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-lambda-repo"
  }
}

resource "aws_ecr_lifecycle_policy" "trading_lambda" {
  repository = aws_ecr_repository.trading_lambda.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 3 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 3
      }
      action = {
        type = "expire"
      }
    }]
  })
}

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.trading_lambda.repository_url
}
