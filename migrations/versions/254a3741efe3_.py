"""Adding back in enforcement of teams.

Revision ID: 254a3741efe3
Revises: f5efc36b3cc9
Create Date: 2019-08-28 21:59:22.176239

"""

# revision identifiers, used by Alembic.
revision = '254a3741efe3'
down_revision = 'f5efc36b3cc9'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    op.add_column('match', sa.Column('enforce_teams', sa.Boolean(), nullable=True))

def downgrade():
    op.drop_column('match', 'enforce_teams')