"""Include private match option, remove enforce teams, include super_admin.

Revision ID: f5efc36b3cc9
Revises: ca309999b2ee
Create Date: 2019-08-22 22:46:24.950968

"""

# revision identifiers, used by Alembic.
revision = 'f5efc36b3cc9'
down_revision = 'ca309999b2ee'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    op.add_column('match', sa.Column('private_match', sa.Boolean(), nullable=True, default=False))
    op.add_column('user', sa.Column('super_admin', sa.Boolean(), nullable=False, default=False))
    op.drop_column('match', 'enforce_teams')

def downgrade():
    op.drop_column('match', 'private_match')
    op.drop_column('user', 'super_admin')
    op.add_column('match', sa.Column('enforce_teams', sa.Boolean(), nullable=True))
