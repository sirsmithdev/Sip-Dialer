#!/bin/bash

echo "Starting API..."

# Run database migrations first (with timeout to prevent hanging)
echo "Running Alembic migrations..."
timeout 60 python -m alembic upgrade head
migration_status=$?

if [ $migration_status -eq 0 ]; then
    echo "Migrations completed successfully."
elif [ $migration_status -eq 124 ]; then
    echo "WARNING: Migrations timed out. Continuing anyway..."
else
    echo "WARNING: Migrations exited with status $migration_status"
    echo "Continuing to start the server anyway..."
fi

echo "Starting uvicorn..."

# Start the API server
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
