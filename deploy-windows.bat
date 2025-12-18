@echo off
REM ============================================================
REM SIP Auto-Dialer - Windows Deployment Script
REM ============================================================
REM This script helps deploy the SIP Auto-Dialer on Windows Server
REM Prerequisites: Docker Desktop for Windows installed and running
REM ============================================================

setlocal EnableDelayedExpansion

echo.
echo ============================================================
echo   SIP Auto-Dialer - Windows Deployment Script
echo ============================================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker Desktop first.
    echo.
    pause
    exit /b 1
)

echo [OK] Docker is running
echo.

REM Check for .env file
if not exist ".env" (
    echo [INFO] No .env file found. Creating from .env.example...
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [OK] Created .env file from .env.example
        echo [IMPORTANT] Please edit .env with your actual configuration values!
        echo.
        notepad .env
        echo.
        echo Press any key after you have configured .env...
        pause >nul
    ) else (
        echo [ERROR] .env.example not found. Please create .env manually.
        pause
        exit /b 1
    )
)

echo [OK] .env file exists
echo.

REM Parse command line arguments
set ACTION=%1
if "%ACTION%"=="" set ACTION=help

if /i "%ACTION%"=="build" goto :build
if /i "%ACTION%"=="start" goto :start
if /i "%ACTION%"=="stop" goto :stop
if /i "%ACTION%"=="restart" goto :restart
if /i "%ACTION%"=="logs" goto :logs
if /i "%ACTION%"=="status" goto :status
if /i "%ACTION%"=="clean" goto :clean
if /i "%ACTION%"=="init" goto :init
if /i "%ACTION%"=="dev" goto :dev
if /i "%ACTION%"=="prod" goto :prod
goto :help

:help
echo Usage: deploy-windows.bat [command]
echo.
echo Commands:
echo   init      - First-time setup (build images, create volumes, init DB)
echo   build     - Build all Docker images
echo   start     - Start all services
echo   stop      - Stop all services
echo   restart   - Restart all services
echo   logs      - View logs (use: logs [service_name])
echo   status    - Show status of all services
echo   clean     - Remove all containers and volumes (DESTRUCTIVE!)
echo   dev       - Start in development mode
echo   prod      - Start in production mode
echo.
echo Examples:
echo   deploy-windows.bat init     - First time setup
echo   deploy-windows.bat start    - Start all services
echo   deploy-windows.bat logs api-gateway - View API logs
echo.
goto :end

:init
echo [STEP 1/4] Building Docker images...
docker-compose build --no-cache
if errorlevel 1 (
    echo [ERROR] Failed to build images
    goto :end
)
echo [OK] Images built successfully
echo.

echo [STEP 2/4] Creating Docker volumes...
docker volume create sip-autodialer-postgres-data >nul 2>&1
docker volume create sip-autodialer-redis-data >nul 2>&1
docker volume create sip-autodialer-minio-data >nul 2>&1
echo [OK] Volumes created
echo.

echo [STEP 3/4] Starting services...
docker-compose up -d
if errorlevel 1 (
    echo [ERROR] Failed to start services
    goto :end
)
echo [OK] Services started
echo.

echo [STEP 4/4] Waiting for database to be ready...
timeout /t 10 /nobreak >nul
echo [OK] Waiting complete
echo.

echo [INFO] Running database migrations...
docker-compose exec -T api-gateway alembic upgrade head
if errorlevel 1 (
    echo [WARNING] Migration may have failed. Check logs for details.
) else (
    echo [OK] Migrations complete
)
echo.

echo ============================================================
echo   Deployment Complete!
echo ============================================================
echo.
echo Services are available at:
echo   - Frontend:    http://localhost:3000
echo   - API:         http://localhost:8000
echo   - API Docs:    http://localhost:8000/docs
echo   - Flower:      http://localhost:5555
echo   - MinIO:       http://localhost:9001
echo.
echo Default admin credentials (CHANGE THESE!):
echo   Username: admin@example.com
echo   Password: changeme123
echo.
echo Use 'deploy-windows.bat logs' to view logs
echo Use 'deploy-windows.bat stop' to stop services
echo.
goto :end

:build
echo Building Docker images...
docker-compose build %2
if errorlevel 1 (
    echo [ERROR] Build failed
) else (
    echo [OK] Build complete
)
goto :end

:start
echo Starting services...
docker-compose up -d
if errorlevel 1 (
    echo [ERROR] Failed to start services
) else (
    echo [OK] Services started
    echo.
    echo Frontend: http://localhost:3000
    echo API:      http://localhost:8000
)
goto :end

:stop
echo Stopping services...
docker-compose down
echo [OK] Services stopped
goto :end

:restart
echo Restarting services...
docker-compose down
docker-compose up -d
echo [OK] Services restarted
goto :end

:logs
set SERVICE=%2
if "%SERVICE%"=="" (
    echo Showing logs for all services (Ctrl+C to exit)...
    docker-compose logs -f
) else (
    echo Showing logs for %SERVICE% (Ctrl+C to exit)...
    docker-compose logs -f %SERVICE%
)
goto :end

:status
echo.
echo Service Status:
echo ===============
docker-compose ps
echo.
echo Docker Resources:
echo =================
docker system df
goto :end

:clean
echo.
echo [WARNING] This will remove ALL containers, volumes, and data!
echo.
set /p CONFIRM="Are you sure? Type 'yes' to confirm: "
if /i not "%CONFIRM%"=="yes" (
    echo Cancelled.
    goto :end
)
echo.
echo Stopping and removing containers...
docker-compose down -v --remove-orphans
echo Removing images...
docker-compose down --rmi local
echo [OK] Cleanup complete
goto :end

:dev
echo Starting in development mode...
docker-compose -f docker-compose.yml up -d
echo [OK] Development environment started
echo.
echo Frontend: http://localhost:3000
echo API:      http://localhost:8000
echo API Docs: http://localhost:8000/docs
goto :end

:prod
echo Starting in production mode...
if exist "docker-compose.prod.yml" (
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
) else (
    echo [WARNING] docker-compose.prod.yml not found, using default config
    docker-compose up -d
)
echo [OK] Production environment started
goto :end

:end
endlocal
