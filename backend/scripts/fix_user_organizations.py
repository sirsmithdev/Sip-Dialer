"""
Script to fix users without organization_id.
Creates a default organization and assigns all users without an org to it.
Run inside the container: python -m scripts.fix_user_organizations
"""
import asyncio
import sys
import os

# Add the backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update
from app.db.session import async_session_maker
from app.models.user import User, Organization


async def fix_user_organizations():
    """Fix users that don't have an organization_id."""
    async with async_session_maker() as session:
        # First, ensure default organization exists
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
            print(f"Created default organization with ID: {org.id}")
        else:
            print(f"Default organization already exists with ID: {org.id}")

        # Find all users without organization_id
        result = await session.execute(
            select(User).where(User.organization_id == None)
        )
        users_without_org = result.scalars().all()

        if not users_without_org:
            print("All users already have an organization assigned.")
            return

        print(f"Found {len(users_without_org)} users without organization:")
        for user in users_without_org:
            print(f"  - {user.email} (role: {user.role.value if user.role else 'unknown'})")

        # Update all users without org to use the default org
        await session.execute(
            update(User)
            .where(User.organization_id == None)
            .values(organization_id=org.id)
        )

        await session.commit()

        print(f"\nSuccessfully assigned {len(users_without_org)} users to the default organization!")


if __name__ == "__main__":
    asyncio.run(fix_user_organizations())
