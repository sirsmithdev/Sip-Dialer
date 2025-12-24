#!/bin/bash

echo "Starting API with migrations..."
echo "DATABASE_URL starts with: ${DATABASE_URL:0:30}..."

# Run database migrations first
echo "Running Alembic migrations..."
python -m alembic upgrade head
migration_status=$?

if [ $migration_status -eq 0 ]; then
    echo "Migrations completed successfully."
else
    echo "WARNING: Migrations failed with status $migration_status"
    echo "Tables may already exist or there may be a connection issue."
    echo "Continuing to start the server anyway..."
fi

echo "Starting uvicorn..."

# Start the API server
# --proxy-headers: Trust X-Forwarded-* headers from reverse proxy (DigitalOcean App Platform)
# --forwarded-allow-ips '*': Allow forwarded headers from any IP (required for cloud platforms)
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*'
