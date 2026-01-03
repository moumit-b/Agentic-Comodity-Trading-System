/**
 * EC2 instance configuration for Streamlit dashboard
 * - Amazon Linux 2023
 * - t3.micro instance
 * - User data script to install and run dashboard
 */

# Latest Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = [var.ec2_ami_owner]

  filter {
    name   = "name"
    values = [var.ec2_ami_name_filter]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# IAM Role for EC2 (to access Secrets Manager)
resource "aws_iam_role" "dashboard" {
  name = "${var.project_name}-dashboard-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-dashboard-role"
  }
}

# Attach policy for Secrets Manager access
resource "aws_iam_policy" "dashboard_secrets" {
  name        = "${var.project_name}-dashboard-secrets-policy"
  description = "Allow dashboard EC2 to read Secrets Manager"

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
    Name = "${var.project_name}-dashboard-secrets-policy"
  }
}

resource "aws_iam_role_policy_attachment" "dashboard_secrets" {
  role       = aws_iam_role.dashboard.name
  policy_arn = aws_iam_policy.dashboard_secrets.arn
}

# Attach CloudWatch Agent policy
resource "aws_iam_role_policy_attachment" "dashboard_cloudwatch" {
  role       = aws_iam_role.dashboard.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

# Instance Profile
resource "aws_iam_instance_profile" "dashboard" {
  name = "${var.project_name}-dashboard-profile"
  role = aws_iam_role.dashboard.name

  tags = {
    Name = "${var.project_name}-dashboard-profile"
  }
}

# User data script to bootstrap dashboard
locals {
  user_data = <<-EOF
    #!/bin/bash
    set -e

    # Update system
    dnf update -y

    # Install Python 3.11, git, and development tools
    dnf install -y python3.11 python3.11-pip git gcc python3.11-devel

    # Install Docker
    dnf install -y docker
    systemctl enable docker
    systemctl start docker

    # Add ec2-user to docker group
    usermod -a -G docker ec2-user

    # Install AWS CLI v2
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    ./aws/install
    rm -rf aws awscliv2.zip

    # Clone repository (replace with your repo URL)
    cd /home/ec2-user
    # git clone https://github.com/YOUR_USERNAME/Agentic-Comodotity-Trading-System.git
    # For now, we'll assume code is deployed via other means

    # Create directory structure
    mkdir -p /opt/trading-system
    cd /opt/trading-system

    # Install uv package manager
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="/root/.cargo/bin:$PATH"

    # Fetch secrets from AWS Secrets Manager
    export AWS_DEFAULT_REGION=${var.aws_region}

    # Get database credentials
    DB_SECRET=$(aws secretsmanager get-secret-value --secret-id ${aws_secretsmanager_secret.rds_password.name} --query SecretString --output text)
    export DATABASE_URL=$(echo $DB_SECRET | python3 -c "import sys, json; s=json.load(sys.stdin); print(f\"postgresql+asyncpg://{s['username']}:{s['password']}@{s['host']}:{s['port']}/{s['database']}\")")

    # Get Redis credentials
    REDIS_SECRET=$(aws secretsmanager get-secret-value --secret-id ${aws_secretsmanager_secret.redis.name} --query SecretString --output text)
    export REDIS_HOST=$(echo $REDIS_SECRET | python3 -c "import sys, json; s=json.load(sys.stdin); print(s['host'])")
    export REDIS_PORT=6379

    # Get Alpaca credentials
    ALPACA_SECRET=$(aws secretsmanager get-secret-value --secret-id ${aws_secretsmanager_secret.alpaca.name} --query SecretString --output text)
    export ALPACA_API_KEY=$(echo $ALPACA_SECRET | python3 -c "import sys, json; s=json.load(sys.stdin); print(s['api_key'])")
    export ALPACA_API_SECRET=$(echo $ALPACA_SECRET | python3 -c "import sys, json; s=json.load(sys.stdin); print(s['api_secret'])")
    export ALPACA_PAPER_TRADING=true

    # Create systemd service for Streamlit
    cat > /etc/systemd/system/trading-dashboard.service <<SERVICE
    [Unit]
    Description=Trading System Dashboard
    After=network.target

    [Service]
    Type=simple
    User=ec2-user
    WorkingDirectory=/opt/trading-system
    Environment="PATH=/root/.cargo/bin:/usr/local/bin:/usr/bin:/bin"
    Environment="DATABASE_URL=$DATABASE_URL"
    Environment="REDIS_HOST=$REDIS_HOST"
    Environment="REDIS_PORT=$REDIS_PORT"
    Environment="ALPACA_API_KEY=$ALPACA_API_KEY"
    Environment="ALPACA_API_SECRET=$ALPACA_API_SECRET"
    Environment="ALPACA_PAPER_TRADING=true"
    ExecStart=/root/.cargo/bin/uv run streamlit run dashboard/app.py --server.port=${var.dashboard_port} --server.address=0.0.0.0
    Restart=always
    RestartSec=10

    [Install]
    WantedBy=multi-user.target
SERVICE

    # Enable and start service
    systemctl daemon-reload
    systemctl enable trading-dashboard
    # systemctl start trading-dashboard  # Start after code is deployed

    # CloudWatch Logs agent configuration
    cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json <<CWCONFIG
    {
      "logs": {
        "logs_collected": {
          "files": {
            "collect_list": [
              {
                "file_path": "/var/log/trading-dashboard.log",
                "log_group_name": "/aws/ec2/${var.project_name}-dashboard",
                "log_stream_name": "{instance_id}"
              }
            ]
          }
        }
      }
    }
CWCONFIG

    # Start CloudWatch agent
    /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
      -a fetch-config \
      -m ec2 \
      -s \
      -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

    echo "Dashboard instance setup complete!"
  EOF
}

# Elastic IP for dashboard
resource "aws_eip" "dashboard" {
  domain = "vpc"

  tags = {
    Name = "${var.project_name}-dashboard-eip"
  }

  depends_on = [aws_internet_gateway.main]
}

# EC2 Instance
resource "aws_instance" "dashboard" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = var.ec2_instance_type
  subnet_id              = aws_subnet.public[0].id
  vpc_security_group_ids = [aws_security_group.dashboard.id]
  iam_instance_profile   = aws_iam_instance_profile.dashboard.name

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.ec2_volume_size
    delete_on_termination = true
    encrypted             = true
  }

  user_data = local.user_data

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # IMDSv2 required
    http_put_response_hop_limit = 1
  }

  tags = {
    Name       = "${var.project_name}-dashboard"
    Component  = "Dashboard"
    CostCenter = "Infrastructure"
  }
}

# Associate Elastic IP
resource "aws_eip_association" "dashboard" {
  instance_id   = aws_instance.dashboard.id
  allocation_id = aws_eip.dashboard.id
}

# CloudWatch Log Group for dashboard logs
resource "aws_cloudwatch_log_group" "dashboard" {
  name              = "/aws/ec2/${var.project_name}-dashboard"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = {
    Name = "${var.project_name}-dashboard-logs"
  }
}
