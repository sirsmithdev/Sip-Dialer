"""Fix user organizations - assign users without org to default org

Revision ID: 012
Revises: 011
Create Date: 2024-12-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import uuid


# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade():
    # Get a connection
    conn = op.get_bind()

    # Check if default organization exists
    result = conn.execute(text("SELECT id FROM organizations WHERE slug = 'default'"))
    org_row = result.fetchone()

    if org_row:
        org_id = org_row[0]
        print(f"Default organization already exists with ID: {org_id}")
    else:
        # Create default organization
        org_id = str(uuid.uuid4())
        conn.execute(text("""
            INSERT INTO organizations (id, name, slug, is_active, max_concurrent_calls, timezone, created_at, updated_at)
            VALUES (:id, 'Default Organization', 'default', true, 10, 'UTC', NOW(), NOW())
        """), {"id": org_id})
        print(f"Created default organization with ID: {org_id}")

    # Count users without organization
    result = conn.execute(text("SELECT COUNT(*) FROM users WHERE organization_id IS NULL"))
    count = result.scalar()

    if count > 0:
        # Update all users without organization to use default org
        conn.execute(text("""
            UPDATE users SET organization_id = :org_id WHERE organization_id IS NULL
        """), {"org_id": org_id})
        print(f"Assigned {count} users to the default organization")
    else:
        print("All users already have an organization assigned")


def downgrade():
    # We don't want to remove organizations from users in downgrade
    pass
