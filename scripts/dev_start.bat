@echo off
REM Start local development environment (PostgreSQL + Redis) - Windows version

echo Starting local development environment...
echo.

REM Start Docker Compose services
docker-compose up -d

REM Wait for services to be healthy
echo Waiting for services to be ready...
timeout /t 5 /nobreak >nul

:check_postgres
docker exec trading_postgres pg_isready -U postgres >nul 2>&1
if errorlevel 1 (
    echo Waiting for PostgreSQL...
    timeout /t 2 /nobreak >nul
    goto check_postgres
)
echo [OK] PostgreSQL is ready

:check_redis
docker exec trading_redis redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo Waiting for Redis...
    timeout /t 2 /nobreak >nul
    goto check_redis
)
echo [OK] Redis is ready

echo.
echo Running database migrations...
alembic upgrade head

echo.
echo ========================================
echo Development environment is ready!
echo ========================================
echo.
echo Services:
echo   - PostgreSQL: localhost:5432
echo     (user: postgres, password: postgres, db: trading_system)
echo   - Redis: localhost:6379 (db: 0)
echo.
echo Commands:
echo   - Stop environment: docker-compose down
echo   - View logs: docker-compose logs -f
echo   - Check status: docker-compose ps
echo.
