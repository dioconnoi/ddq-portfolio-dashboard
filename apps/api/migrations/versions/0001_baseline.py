"""baseline: no data tables yet; proves the migration pipeline and locks down alembic_version

Revision ID: 0001
Revises:
Create Date: 2026-09-24
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # alembic_version lives in `public`, which Supabase exposes over REST; deny-all it.
    op.execute("ALTER TABLE alembic_version ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("ALTER TABLE alembic_version DISABLE ROW LEVEL SECURITY")
