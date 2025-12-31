#!/bin/bash
# Start local development environment (PostgreSQL + Redis)

echo "Starting local development environment..."

# Start Docker Compose services
docker-compose up -d

# Wait for services to be healthy
echo "Waiting for services to be ready..."
sleep 5

# Check PostgreSQL
until docker exec trading_postgres pg_isready -U postgres > /dev/null 2>&1; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done
echo "✓ PostgreSQL is ready"

# Check Redis
until docker exec trading_redis redis-cli ping > /dev/null 2>&1; do
  echo "Waiting for Redis..."
  sleep 2
done
echo "✓ Redis is ready"

# Run Alembic migrations
echo "Running database migrations..."
alembic upgrade head

echo ""
echo "Development environment is ready!"
echo ""
echo "Services:"
echo "  - PostgreSQL: localhost:5432 (user: postgres, password: postgres, db: trading_system)"
echo "  - Redis: localhost:6379 (db: 0)"
echo ""
echo "To stop: docker-compose down"
echo "To view logs: docker-compose logs -f"
