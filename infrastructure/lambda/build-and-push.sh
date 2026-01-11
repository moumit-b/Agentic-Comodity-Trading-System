#!/bin/bash
set -e

AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/trading-system-lambda"

echo "Building and pushing Lambda container images to ECR..."
echo "ECR Repository: $ECR_REPO"

# Navigate to project root for build context
cd ../..

# Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Build trading loop image from project root for linux/amd64
# Using regular docker build (not buildx) to avoid manifest list format issues with Lambda
echo "Building trading-loop image for linux/amd64..."
docker build --platform linux/amd64 -t trading-loop -f infrastructure/lambda/Dockerfile.trading_loop .
docker tag trading-loop:latest ${ECR_REPO}:trading-loop-latest
echo "Pushing trading-loop image..."
docker push ${ECR_REPO}:trading-loop-latest

# Build settlement image from project root for linux/amd64
echo "Building settlement image for linux/amd64..."
docker build --platform linux/amd64 -t settlement -f infrastructure/lambda/Dockerfile.settlement .
docker tag settlement:latest ${ECR_REPO}:settlement-latest
echo "Pushing settlement image..."
docker push ${ECR_REPO}:settlement-latest

echo "✓ Images pushed to ECR successfully!"
echo "  - ${ECR_REPO}:trading-loop-latest"
echo "  - ${ECR_REPO}:settlement-latest"
