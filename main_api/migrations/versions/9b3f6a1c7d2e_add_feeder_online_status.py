from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9b3f6a1c7d2e'
down_revision: Union[str, Sequence[str], None] = '7a1f9c2e4b6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('feeders', sa.Column('is_online', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column(
        'system_settings',
        sa.Column(
            'feeder_offline_retry_interval', sa.Integer(), nullable=False, server_default='300'
        )
    )


def downgrade() -> None:
    op.drop_column('system_settings', 'feeder_offline_retry_interval')
    op.drop_column('feeders', 'is_online')
