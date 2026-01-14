#!/bin/bash
# Build Lambda function packages INCLUDING source code

set -e

echo "Building Lambda function packages (with src/)..."

# Ensure we are in project root
if [ ! -d "src" ]; then
    echo "Error: Must run from project root (where src/ directory is)"
    exit 1
fi

# Create build directory
mkdir -p build/trading_loop

# Copy handler
cp infrastructure/lambda/trading_loop/handler.py build/trading_loop/
# Copy requirements (if needed by Lambda layer builder, though not used directly here)
cp infrastructure/lambda/trading_loop/requirements.txt build/trading_loop/

# Copy source code
echo "Copying src/ directory..."
cp -r src build/trading_loop/

# Create Zip
echo "Zipping trading_loop..."
cd build/trading_loop
zip -r ../../trading_loop.zip .
cd ../..

SIZE=$(du -h trading_loop.zip | cut -f1)
echo "✓ trading_loop.zip created ($SIZE)"

echo ""
echo "Upload with:"
echo "  aws lambda update-function-code --function-name trading-system-trading-loop --zip-file fileb://trading_loop.zip --region us-east-1"

# Clean up
rm -rf build
