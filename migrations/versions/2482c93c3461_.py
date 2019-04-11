"""empty message

Revision ID: 2482c93c3461
Revises: 6fff5b509b3b
Create Date: 2019-04-11 17:17:11.094093

"""

# revision identifiers, used by Alembic.
revision = '2482c93c3461'
down_revision = '6fff5b509b3b'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    op.add_column('match', sa.Column('veto_first', mysql.VARCHAR(length=5), nullable=True))
    


def downgrade():
    op.drop_column('match', 'veto_first')

