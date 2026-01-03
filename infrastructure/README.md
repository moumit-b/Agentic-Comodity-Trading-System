# AWS Infrastructure Deployment Guide

This directory contains Terraform infrastructure-as-code and Lambda handlers for deploying the trading system to AWS.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         AWS Cloud                            │
│                                                              │
│  ┌──────────────┐     ┌──────────────┐    ┌─────────────┐  │
│  │ EventBridge  │────▶│   Lambda     │───▶│  RDS PG     │  │
│  │ (1min cron)  │     │ Trading Loop │    │ (db.t3.mic) │  │
│  └──────────────┘     └──────────────┘    └─────────────┘  │
│                              │                    │          │
│  ┌──────────────┐            │             ┌─────────────┐  │
│  │ EventBridge  │            └────────────▶│ ElastiCache │  │
│  │ (4pm daily)  │                          │  Redis      │  │
│  └──────────────┘     ┌──────────────┐    │(cache.t3.m) │  │
│         │             │   Lambda     │    └─────────────┘  │
│         └────────────▶│  Settlement  │           │          │
│                       └──────────────┘           │          │
│                                                  │          │
│  ┌──────────────┐     ┌──────────────┐          │          │
│  │  Public IP   │────▶│     EC2      │──────────┘          │
│  │ (Dashboard)  │     │ t3.micro     │                     │
│  └──────────────┘     │ Streamlit    │                     │
│                       └──────────────┘                     │
│                                                              │
│  VPC: 10.0.0.0/16                                           │
│  ├─ Public Subnets: 10.0.1.0/24, 10.0.2.0/24               │
│  └─ Private Subnets: 10.0.10.0/24, 10.0.11.0/24            │
└─────────────────────────────────────────────────────────────┘
```

**Estimated Monthly Cost:** ~$42 USD
- RDS PostgreSQL (db.t3.micro): ~$15
- ElastiCache Redis (cache.t3.micro): ~$12
- EC2 Dashboard (t3.micro): ~$8
- NAT Gateway: ~$5
- Secrets Manager: ~$2

## Prerequisites

1. **AWS Account** with sufficient permissions
2. **Terraform** >= 1.6 installed ([download](https://www.terraform.io/downloads))
3. **AWS CLI v2** configured with credentials
4. **Python 3.11** for building Lambda packages
5. **Docker** (optional, for layer building)

## Quick Start

### 1. Configure Variables

Create `terraform/terraform.tfvars`:

```hcl
# Required variables
owner_email           = "your-email@example.com"
alarm_email           = "your-email@example.com"
alpaca_api_key        = "YOUR_ALPACA_API_KEY"
alpaca_api_secret     = "YOUR_ALPACA_API_SECRET"

# Optional variables
aws_region            = "us-east-1"
environment           = "production"
project_name          = "trading-system"
discord_webhook_url   = "https://discord.com/api/webhooks/YOUR_WEBHOOK"

# Security: Restrict SSH access to your IP
ssh_allowed_cidr      = ["YOUR_IP/32"]  # e.g., ["203.0.113.25/32"]
```

**IMPORTANT:** Add `terraform.tfvars` to `.gitignore` to protect secrets!

### 2. Build Lambda Packages

```bash
# Navigate to infrastructure directory
cd infrastructure

# Build Lambda layer (shared dependencies)
./scripts/build_lambda_layer.sh

# Build Lambda functions
./scripts/build_lambda_functions.sh
```

This creates:
- `lambda/layer.zip` - Shared dependencies layer
- `lambda/trading_loop.zip` - Trading loop handler
- `lambda/settlement.zip` - Settlement handler

### 3. Deploy Infrastructure

```bash
cd terraform

# Initialize Terraform
terraform init

# Review planned changes
terraform plan

# Apply infrastructure (will prompt for confirmation)
terraform apply

# Save outputs for reference
terraform output > ../deployment_outputs.txt
```

**Deployment time:** ~15-20 minutes

### 4. Post-Deployment Steps

After `terraform apply` completes:

#### a. Confirm SNS Email Subscription
Check your email (`alarm_email`) and confirm the CloudWatch alarms subscription.

#### b. Deploy Application Code to EC2

```bash
# Get dashboard public IP
DASHBOARD_IP=$(terraform output -raw dashboard_public_ip)

# SSH to instance (if SSH access enabled)
ssh ec2-user@$DASHBOARD_IP

# OR use AWS Systems Manager Session Manager (no SSH key required)
aws ssm start-session --target $(terraform output -raw dashboard_instance_id)
```

On the EC2 instance:

```bash
# Clone repository (replace with your repo URL)
cd /opt/trading-system
git clone https://github.com/YOUR_USERNAME/Agentic-Comodotity-Trading-System.git .

# Install dependencies with uv
uv sync

# Run database migrations
uv run alembic upgrade head

# Start dashboard service
sudo systemctl start trading-dashboard
sudo systemctl status trading-dashboard

# View logs
sudo journalctl -u trading-dashboard -f
```

#### c. Upload Lambda Deployment Packages

The Lambda functions are created but need code uploaded:

```bash
# Update trading loop function
aws lambda update-function-code \
  --function-name trading-system-trading-loop \
  --zip-file fileb://lambda/trading_loop.zip

# Update settlement function
aws lambda update-function-code \
  --function-name trading-system-settlement \
  --zip-file fileb://lambda/settlement.zip

# Update layer
aws lambda publish-layer-version \
  --layer-name trading-system-dependencies \
  --zip-file fileb://lambda/layer.zip \
  --compatible-runtimes python3.11
```

#### d. Test Lambda Functions

```bash
# Test trading loop (manual invocation)
aws lambda invoke \
  --function-name trading-system-trading-loop \
  --payload '{}' \
  response.json

cat response.json

# Test settlement
aws lambda invoke \
  --function-name trading-system-settlement \
  --payload '{}' \
  response.json

cat response.json
```

#### e. Verify EventBridge Schedules

```bash
# Check EventBridge rules
aws events list-rules --name-prefix trading-system

# Check next scheduled execution
aws events describe-rule --name trading-system-trading-loop-schedule
```

## Accessing the Dashboard

The Streamlit dashboard is accessible at:

```
http://<DASHBOARD_IP>:8501
```

Get the IP:
```bash
terraform output dashboard_url
```

## Monitoring

### CloudWatch Dashboards

- Lambda logs: `/aws/lambda/trading-system-trading-loop`
- Settlement logs: `/aws/lambda/trading-system-settlement`
- Dashboard logs: `/aws/ec2/trading-system-dashboard`

### CloudWatch Alarms

15 alarms configured:
- Lambda errors (trading loop, settlement)
- Lambda duration (approaching timeout)
- Lambda throttles
- RDS CPU, storage, connections
- Redis CPU, memory
- EC2 status checks, CPU
- NAT Gateway packet drops

All alarms send notifications to SNS topic → Email

### View Metrics

```bash
# CloudWatch Logs Insights query example
aws logs start-query \
  --log-group-name /aws/lambda/trading-system-trading-loop \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc'
```

## Cost Optimization

1. **Single AZ Deployment:** Multi-AZ disabled for RDS and Redis (~50% savings)
2. **t3.micro Instances:** Smallest production-capable instances
3. **Scheduled Lambda:** Only runs during market hours (9 AM - 4 PM ET, Mon-Fri)
4. **Log Retention:** 14 days (reduce CloudWatch costs)
5. **Snapshot Retention:** 5 days for Redis, 7 days for RDS

**Further Optimization:**
- Enable VPC endpoints for S3 to reduce NAT Gateway data transfer costs
- Use Savings Plans or Reserved Instances for predictable workloads

## Security

### Network Security
- Private subnets for RDS, Redis, Lambda
- Security groups restrict access to required ports only
- IMDSv2 required on EC2
- NAT Gateway for Lambda outbound internet access

### Secrets Management
- All credentials stored in AWS Secrets Manager
- Automatic secret rotation supported (not enabled by default)
- IAM policies grant least-privilege access

### Encryption
- RDS encryption at rest enabled
- ElastiCache encryption at rest enabled
- EBS volumes encrypted
- Secrets Manager encryption enabled

## Maintenance

### Update Lambda Code

```bash
# Build new package
./scripts/build_lambda_functions.sh

# Deploy update
aws lambda update-function-code \
  --function-name trading-system-trading-loop \
  --zip-file fileb://lambda/trading_loop.zip
```

### Scale Resources

Edit `terraform/terraform.tfvars`:

```hcl
# Increase RDS instance size
rds_instance_class = "db.t3.small"  # Default: db.t3.micro

# Increase Lambda memory
lambda_trading_loop_memory = 1024  # Default: 512
```

Apply changes:
```bash
terraform apply
```

### Database Backups

RDS automated backups:
- Retention: 7 days
- Backup window: 03:00-04:00 UTC
- Point-in-time recovery enabled

Manual snapshot:
```bash
aws rds create-db-snapshot \
  --db-instance-identifier trading-system-postgres \
  --db-snapshot-identifier trading-system-manual-$(date +%Y%m%d)
```

## Disaster Recovery

### Restore from RDS Snapshot

```bash
# List snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier trading-system-postgres

# Restore
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier trading-system-postgres-restored \
  --db-snapshot-identifier SNAPSHOT_ID
```

### Backup Secrets

```bash
# Export secrets (secure this file!)
aws secretsmanager get-secret-value \
  --secret-id trading-system/alpaca/credentials \
  > secrets-backup.json
```

## Teardown

To destroy all infrastructure:

```bash
cd terraform

# Disable deletion protection on RDS first
aws rds modify-db-instance \
  --db-instance-identifier trading-system-postgres \
  --no-deletion-protection

# Destroy infrastructure
terraform destroy
```

**WARNING:** This will delete all data! Ensure you have backups.

## Troubleshooting

### Lambda Timeout
- Increase timeout in `variables.tf`
- Check CloudWatch logs for slow queries
- Verify VPC NAT Gateway connectivity

### Dashboard Not Accessible
- Check EC2 security group allows port 8501
- Verify Elastic IP association
- Check systemd service: `systemctl status trading-dashboard`

### Database Connection Errors
- Verify security group allows connections from Lambda/EC2
- Check RDS endpoint in Secrets Manager
- Verify VPC routing to private subnets

### High Costs
- Check CloudWatch billing metrics
- Review NAT Gateway data transfer
- Verify EventBridge schedules are correct (market hours only)

## Support

For issues or questions:
1. Check CloudWatch Logs
2. Review Terraform outputs
3. Check AWS Service Health Dashboard
4. Review project documentation in `docs/`

## License

See main project LICENSE file.
