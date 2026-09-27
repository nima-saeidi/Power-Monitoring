from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '088d59b31213'
down_revision: Union[str, Sequence[str], None] = 'aa889adcb5e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('feeders', sa.Column('port', sa.Integer(), nullable=True))
    op.add_column('feeders', sa.Column('active_power_register', sa.Integer(), nullable=True))
    op.add_column('feeders', sa.Column('reactive_power_register', sa.Integer(), nullable=True))
    op.add_column('feeders', sa.Column('voltage_register', sa.Integer(), nullable=True))
    op.add_column('feeders', sa.Column('current_register', sa.Integer(), nullable=True))
    op.add_column('feeders', sa.Column('power_factor_register', sa.Integer(), nullable=True))
    op.drop_column('locations', 'longitude')
    op.drop_column('locations', 'latitude')


def downgrade() -> None:
    op.add_column('locations', sa.Column('latitude', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.add_column('locations', sa.Column('longitude', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.drop_column('feeders', 'power_factor_register')
    op.drop_column('feeders', 'current_register')
    op.drop_column('feeders', 'voltage_register')
    op.drop_column('feeders', 'reactive_power_register')
    op.drop_column('feeders', 'active_power_register')
    op.drop_column('feeders', 'port')
