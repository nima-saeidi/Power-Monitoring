from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c7e9a4d6f1'
down_revision: Union[str, Sequence[str], None] = 'f1b8d4e6a9c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'command_challenges',
        sa.Column('jti', sa.String(length=32), primary_key=True),
        sa.Column('failed_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('consumed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_command_challenges_expires_at', 'command_challenges', ['expires_at'])


def downgrade() -> None:
    op.drop_index('ix_command_challenges_expires_at', table_name='command_challenges')
    op.drop_table('command_challenges')
