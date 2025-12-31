#!/bin/bash
# Stop local development environment

echo "Stopping local development environment..."

docker-compose down

echo "✓ Development environment stopped"
echo ""
echo "Note: Data volumes are preserved. Use 'docker-compose down -v' to delete all data."
