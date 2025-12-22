"""
Script to create an admin user.
Run inside the container: python -m scripts.create_admin

This script will:
1. Run database migrations to ensure tables exist
2. Create a default organization if needed
3. Create an admin user if one doesn't exist
"""
import asyncio
import subprocess
import sys
import os

# Add the backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.db.session import async_session_maker
from app.models.user import User, UserRole, Organization
from app.core.security import get_password_hash


def run_migrations():
    """Run alembic migrations before creating the admin user."""
    print("Running database migrations...")
    try:
        result = subprocess.run(
            ["python", "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        if result.returncode != 0:
            print(f"Migration stderr: {result.stderr}")
            # Don't fail - tables might already exist
            print("Warning: Migrations may have failed, but continuing...")
        else:
            print("Migrations completed successfully.")
            if result.stdout:
                print(result.stdout)
    except Exception as e:
        print(f"Error running migrations: {e}")
        print("Continuing anyway - tables may already exist...")


async def create_admin_user():
    """Create a test admin user."""
    async with async_session_maker() as session:
        # Check if admin already exists
        result = await session.execute(
            select(User).where(User.email == "admin@example.com")
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print("Admin user already exists!")
            print(f"  Email: {existing_user.email}")
            print(f"  Role: {existing_user.role.value}")
            print(f"  Is Superuser: {existing_user.is_superuser}")
            return

        # Create default organization first
        result = await session.execute(
            select(Organization).where(Organization.slug == "default")
        )
        org = result.scalar_one_or_none()

        if not org:
            org = Organization(
                name="Default Organization",
                slug="default",
                is_active=True,
                max_concurrent_calls=10,
                timezone="UTC"
            )
            session.add(org)
            await session.flush()
            print("Created default organization")

        # Create admin user - use string value for role since DB uses VARCHAR not ENUM
        hashed_pwd = get_password_hash("admin123")

        # Insert directly via raw SQL to avoid enum type issues
        from sqlalchemy import text
        import uuid

        user_id = str(uuid.uuid4())
        await session.execute(
            text("""
                INSERT INTO users (id, email, hashed_password, first_name, last_name,
                                   is_active, is_superuser, role, organization_id)
                VALUES (:id, :email, :hashed_password, :first_name, :last_name,
                        :is_active, :is_superuser, :role, :organization_id)
            """),
            {
                "id": user_id,
                "email": "admin@example.com",
                "hashed_password": hashed_pwd,
                "first_name": "Admin",
                "last_name": "User",
                "is_active": True,
                "is_superuser": True,
                "role": "admin",
                "organization_id": str(org.id)
            }
        )

        await session.commit()

        print("\n" + "=" * 50)
        print("Admin user created successfully!")
        print("=" * 50)
        print(f"  Email: admin@example.com")
        print(f"  Password: admin123")
        print(f"  Role: admin")
        print(f"  Is Superuser: True")
        print("=" * 50)


if __name__ == "__main__":
    # Run migrations first to ensure tables exist
    run_migrations()
    # Then create the admin user
    asyncio.run(create_admin_user())
