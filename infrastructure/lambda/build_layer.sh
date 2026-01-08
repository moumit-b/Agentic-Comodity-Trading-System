#!/bin/bash
# Build Lambda layer using Docker for Linux compatibility
# This ensures the layer works on AWS Lambda (Amazon Linux 2)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==================================="
echo "Building Lambda Layer with Docker"
echo "==================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Clean up previous builds
echo -e "${YELLOW}Cleaning up previous builds...${NC}"
rm -rf python/
rm -f layer.zip

# Create Dockerfile for build
echo -e "${YELLOW}Creating build Dockerfile...${NC}"
cat > Dockerfile.lambda-layer <<'EOF'
FROM public.ecr.aws/lambda/python:3.11

# Install build dependencies
RUN yum install -y \
    gcc \
    g++ \
    make \
    cmake \
    unzip \
    libpq-devel \
    && yum clean all

# Copy requirements
COPY trading_loop/requirements.txt /tmp/requirements.txt

# Create python directory
WORKDIR /tmp
RUN mkdir -p python

# Install Python dependencies
RUN pip install \
    --target python \
    --upgrade \
    -r requirements.txt \
    --no-cache-dir

# Remove unnecessary files to reduce layer size
RUN cd python && \
    find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find . -type d -name "*.dist-info" -exec rm -rf {}/licenses {} + 2>/dev/null || true && \
    find . -name "*.pyc" -delete && \
    find . -name "*.pyo" -delete && \
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find . -name "*.so" -exec strip {} + 2>/dev/null || true

# Package the layer
RUN cd /tmp && zip -r layer.zip python -x "*.pyc" "*.pyo" "*__pycache__*"

CMD ["bash"]
EOF

# Build Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -f Dockerfile.lambda-layer -t lambda-layer-builder .

# Run container and extract layer.zip
echo -e "${YELLOW}Running container to build layer...${NC}"
CONTAINER_ID=$(docker create lambda-layer-builder)
echo "Container ID: $CONTAINER_ID"

echo -e "${YELLOW}Extracting layer.zip from container...${NC}"
docker cp "$CONTAINER_ID:/tmp/layer.zip" ./layer.zip

echo -e "${YELLOW}Extracting python directory from container for inspection...${NC}"
docker cp "$CONTAINER_ID:/tmp/python" ./python

# Clean up container
echo -e "${YELLOW}Cleaning up container...${NC}"
docker rm "$CONTAINER_ID"

# Show layer size
LAYER_SIZE=$(du -h layer.zip | cut -f1)
echo -e "${GREEN}✓ Layer built successfully!${NC}"
echo "Layer size: $LAYER_SIZE"

# List installed packages
echo -e "${YELLOW}Installed packages:${NC}"
ls -lh python/lib/python3.11/site-packages/ | head -20

echo ""
echo -e "${GREEN}==================================="
echo "Build Complete!"
echo "===================================${NC}"
echo ""
echo "Next steps:"
echo "1. Upload layer to S3:"
echo "   aws s3 cp layer.zip s3://\$BUCKET_NAME/layers/dependencies-\$(md5sum layer.zip | cut -d' ' -f1).zip"
echo ""
echo "2. Update Lambda function to use new layer version"
echo "   (or run terraform apply to update automatically)"
