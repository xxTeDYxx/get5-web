"""Including ForceTeams in database for use in CVARs.

Revision ID: eced4825e99b
Revises: bc790ce2c7b1
Create Date: 2019-07-30 21:11:53.883048

"""

# revision identifiers, used by Alembic.
revision = 'eced4825e99b'
down_revision = 'bc790ce2c7b1'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    op.add_column('match', sa.Column('enforce_teams', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('match', 'enforce_teams')