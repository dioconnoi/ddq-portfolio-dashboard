"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

Every new table MUST end with:
    op.execute("ALTER TABLE <name> ENABLE ROW LEVEL SECURITY")
The RLS guard test in tests/integration/test_database.py fails the build otherwise.
Migrations must be backward compatible with the previous app version (expand, then contract).
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
