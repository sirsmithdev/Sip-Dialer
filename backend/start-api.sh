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

# Create admin user if it doesn't exist
echo "Ensuring admin user exists..."
python -c "
import asyncio
import sys
import traceback
sys.path.insert(0, '/app')

async def create_admin():
    from sqlalchemy import select, text
    from app.db.session import async_session_maker
    from app.models.user import User, Organization
    from app.core.security import get_password_hash
    import uuid

    print('Connecting to database...')
    async with async_session_maker() as session:
        try:
            # First, check what schema we're in
            result = await session.execute(text('SELECT current_schema()'))
            current_schema = result.scalar()
            print(f'Current schema: {current_schema}')

            # Check search_path
            result = await session.execute(text('SHOW search_path'))
            search_path = result.scalar()
            print(f'Search path: {search_path}')

            # List available schemas
            result = await session.execute(text(
                \"SELECT schema_name FROM information_schema.schemata ORDER BY schema_name\"
            ))
            schemas = [r[0] for r in result.fetchall()]
            print(f'Available schemas: {schemas}')

            # Check if users table exists
            result = await session.execute(text('''
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_name = 'users'
            '''))
            user_tables = result.fetchall()
            print(f'Users table locations: {user_tables}')

        except Exception as e:
            print(f'Schema check failed: {e}')

        try:
            # Check if admin already exists
            result = await session.execute(
                select(User).where(User.email == 'admin@example.com')
            )
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print('Admin user already exists.')
                return

            # Create default organization first
            result = await session.execute(
                select(Organization).where(Organization.slug == 'default')
            )
            org = result.scalar_one_or_none()

            if not org:
                org = Organization(
                    name='Default Organization',
                    slug='default',
                    is_active=True,
                    max_concurrent_calls=10,
                    timezone='UTC'
                )
                session.add(org)
                await session.flush()
                print('Created default organization')

            # Create admin user via raw SQL to avoid enum issues
            hashed_pwd = get_password_hash('admin123')
            user_id = str(uuid.uuid4())
            await session.execute(
                text('''
                    INSERT INTO users (id, email, hashed_password, first_name, last_name,
                                       is_active, is_superuser, role, organization_id)
                    VALUES (:id, :email, :hashed_password, :first_name, :last_name,
                            :is_active, :is_superuser, :role, :organization_id)
                '''),
                {
                    'id': user_id,
                    'email': 'admin@example.com',
                    'hashed_password': hashed_pwd,
                    'first_name': 'Admin',
                    'last_name': 'User',
                    'is_active': True,
                    'is_superuser': True,
                    'role': 'admin',
                    'organization_id': str(org.id)
                }
            )

            await session.commit()
            print('Admin user created: admin@example.com / admin123')
        except Exception as e:
            print(f'Admin creation error: {e}')
            traceback.print_exc()
            # Don't fail - let the server start anyway

asyncio.run(create_admin())
" 2>&1 || echo "Admin creation script failed but continuing..."

echo "Starting uvicorn..."

# Start the API server
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
