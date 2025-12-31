# Development Scripts

Utility scripts for managing the local development environment.

## Quick Start

### Windows

```bash
# Start PostgreSQL + Redis
scripts\dev_start.bat

# Stop environment
scripts\dev_stop.bat
```

### Linux/Mac

```bash
# Make scripts executable
chmod +x scripts/dev_start.sh scripts/dev_stop.sh

# Start PostgreSQL + Redis
./scripts/dev_start.sh

# Stop environment
./scripts/dev_stop.sh
```

## What Gets Started

1. **PostgreSQL 16** (localhost:5432)
   - Database: `trading_system`
   - User: `postgres`
   - Password: `postgres`
   - Persistent volume: `postgres_data`

2. **Redis 7** (localhost:6379)
   - DB: 0
   - Max memory: 256MB (LRU eviction)
   - Persistent volume: `redis_data`

## Manual Docker Compose Commands

```bash
# Start services
docker-compose up -d

# Stop services (keeps data)
docker-compose down

# Stop and remove all data
docker-compose down -v

# View logs
docker-compose logs -f

# Check service status
docker-compose ps

# Restart a specific service
docker-compose restart postgres
docker-compose restart redis
```

## Database Management

```bash
# Run migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Check current version
alembic current

# Create new migration
alembic revision --autogenerate -m "description"

# Connect to PostgreSQL (requires psql)
docker exec -it trading_postgres psql -U postgres -d trading_system
```

## Redis Management

```bash
# Connect to Redis CLI
docker exec -it trading_redis redis-cli

# Common Redis commands (once in redis-cli):
# > PING                  # Test connection
# > KEYS *                # List all keys
# > FLUSHDB               # Clear current database
# > INFO memory           # Check memory usage
# > TTL bars:1m:USO       # Check TTL on a key
```

## Troubleshooting

### Port Already in Use

If port 5432 or 6379 is already in use:

```bash
# Check what's using the port (Windows)
netstat -ano | findstr :5432
netstat -ano | findstr :6379

# Check what's using the port (Linux/Mac)
lsof -i :5432
lsof -i :6379

# Option 1: Stop the conflicting service
# Option 2: Edit docker-compose.yml to use different ports
```

### Services Won't Start

```bash
# Check Docker is running
docker --version
docker ps

# View detailed logs
docker-compose logs postgres
docker-compose logs redis

# Restart Docker Desktop (if on Windows/Mac)
```

### Database Connection Issues

```bash
# Verify PostgreSQL is healthy
docker exec trading_postgres pg_isready -U postgres

# Check connection from host
psql -h localhost -p 5432 -U postgres -d trading_system

# If using WSL2 on Windows, use host.docker.internal instead of localhost
```

## Data Persistence

Data is stored in Docker volumes and persists between container restarts:

- **postgres_data**: All PostgreSQL database files
- **redis_data**: Redis RDB snapshots and AOF logs

To inspect volumes:

```bash
# List volumes
docker volume ls

# Inspect a volume
docker volume inspect trading_postgres_data
docker volume inspect trading_redis_data

# Remove volumes (WARNING: deletes all data)
docker volume rm trading_postgres_data trading_redis_data
```

## Development Workflow

1. Start environment: `scripts\dev_start.bat`
2. Run migrations: `alembic upgrade head`
3. Develop and test your code
4. Stop environment when done: `scripts\dev_stop.bat`

Data persists between sessions, so you don't lose your work!
