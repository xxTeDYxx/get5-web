"""Include series score in matches for advantage/disadvantage.

Revision ID: 95413eb5e8bd
Revises: eced4825e99b
Create Date: 2019-08-16 13:57:08.933645

"""

# revision identifiers, used by Alembic.
revision = '95413eb5e8bd'
down_revision = 'eced4825e99b'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    op.add_column('match', sa.Column('team1_series_score', sa.Integer(), nullable=True))
    op.add_column('match', sa.Column('team2_series_score', sa.Integer(), nullable=True))

def downgrade():
    op.drop_column('match', 'team1_series_score')
    op.drop_column('match', 'team2_series_score')
    
