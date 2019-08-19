"""Include spectators in match page, and in config.

Revision ID: ca309999b2ee
Revises: 95413eb5e8bd
Create Date: 2019-08-18 11:43:49.809510

"""

# revision identifiers, used by Alembic.
revision = 'ca309999b2ee'
down_revision = '95413eb5e8bd'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    op.add_column('match', sa.Column('spectator_auths', sa.PickleType(), nullable=True))

def downgrade():
    op.drop_column('match', 'spectator_auths')
