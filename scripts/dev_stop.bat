@echo off
REM Stop local development environment - Windows version

echo Stopping local development environment...
echo.

docker-compose down

echo.
echo [OK] Development environment stopped
echo.
echo Note: Data volumes are preserved.
echo To delete all data: docker-compose down -v
echo.
