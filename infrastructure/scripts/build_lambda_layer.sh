#!/bin/bash
# Build Lambda layer with shared dependencies

set -e

echo "Building Lambda layer with dependencies..."

# Navigate to lambda directory
cd "$(dirname "$0")/../lambda"

# Create layer directory structure
mkdir -p layer/python/lib/python3.11/site-packages

# Install dependencies
echo "Installing dependencies to layer..."
pip install \
  -r trading_loop/requirements.txt \
  -t layer/python/lib/python3.11/site-packages \
  --upgrade

# Copy source code to layer (so it's available to Lambda functions)
echo "Copying source code to layer..."
cp -r ../../src layer/python/lib/python3.11/site-packages/

# Create zip file
echo "Creating layer.zip..."
cd layer
zip -r ../layer.zip . -x "*.pyc" -x "__pycache__/*" -x "*.dist-info/*"
cd ..

# Cleanup
rm -rf layer

# Get zip size
SIZE=$(du -h layer.zip | cut -f1)
echo "✓ Lambda layer built successfully: layer.zip ($SIZE)"
echo "  Upload with: aws lambda publish-layer-version --layer-name trading-system-dependencies --zip-file fileb://layer.zip"
