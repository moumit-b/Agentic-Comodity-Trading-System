#!/bin/bash
# Build Lambda function deployment packages

set -e

echo "Building Lambda function packages..."

# Navigate to lambda directory
cd "$(dirname "$0")/../lambda"

# Build trading_loop function
echo "Building trading_loop.zip..."
cd trading_loop
zip -r ../trading_loop.zip handler.py requirements.txt
cd ..

SIZE=$(du -h trading_loop.zip | cut -f1)
echo "✓ trading_loop.zip created ($SIZE)"

# Build settlement function
echo "Building settlement.zip..."
cd settlement
zip -r ../settlement.zip handler.py requirements.txt
cd ..

SIZE=$(du -h settlement.zip | cut -f1)
echo "✓ settlement.zip created ($SIZE)"

echo ""
echo "Lambda function packages built successfully!"
echo ""
echo "Upload with:"
echo "  aws lambda update-function-code --function-name trading-system-trading-loop --zip-file fileb://trading_loop.zip"
echo "  aws lambda update-function-code --function-name trading-system-settlement --zip-file fileb://settlement.zip"
