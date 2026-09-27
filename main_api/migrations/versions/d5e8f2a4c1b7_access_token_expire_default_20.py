from typing import Sequence, Union

from alembic import op


revision: str = 'd5e8f2a4c1b7'
down_revision: Union[str, Sequence[str], None] = '9b3f6a1c7d2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('system_settings', 'access_token_expire_minutes', server_default='20')
    op.execute(
        "UPDATE system_settings SET access_token_expire_minutes = 20 "
        "WHERE access_token_expire_minutes = 1440"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE system_settings SET access_token_expire_minutes = 1440 "
        "WHERE access_token_expire_minutes = 20"
    )
    op.alter_column('system_settings', 'access_token_expire_minutes', server_default=None)
