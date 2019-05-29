"""Include encryption on passwords.

Revision ID: ae2ba46fe1a2
Revises: 4e186245e39b
Create Date: 2019-05-02 05:08:50.813840

"""

# revision identifiers, used by Alembic.
revision = 'ae2ba46fe1a2'
down_revision = '4e186245e39b'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    op.alter_column('game_server', 'rcon_password',
               existing_type=mysql.VARCHAR(length=32),
               type_=sa.String(length=128),
               existing_nullable=True)


def downgrade():
    op.alter_column('game_server', 'rcon_password',
               existing_type=sa.String(length=128),
               type_=mysql.VARCHAR(length=32),
               existing_nullable=True)
    ### end Alembic commands ###
