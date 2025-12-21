#!/bin/bash
set -e

echo "Starting API with migrations..."

# Run database migrations first
echo "Running Alembic migrations..."
python -m alembic upgrade head

echo "Migrations complete. Starting uvicorn..."

# Start the API server
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
