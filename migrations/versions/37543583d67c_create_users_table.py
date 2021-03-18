"""Create users table

Revision ID: 37543583d67c
Revises: 
Create Date: 2021-03-18 09:28:31.204003

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '37543583d67c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('username', sa.String(50), primary_key=True),
        sa.Column('password', sa.String(12))
    )

def downgrade():
    op.drop_table('notes')
