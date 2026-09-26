"""set access token expire default to 20 minutes

Revision ID: d5e8f2a4c1b7
Revises: 9b3f6a1c7d2e
Create Date: 2026-09-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd5e8f2a4c1b7'
down_revision: Union[str, Sequence[str], None] = '9b3f6a1c7d2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('system_settings', 'access_token_expire_minutes', server_default='20')
    # فقط ردیف‌هایی که هنوز روی پیش‌فرض قدیمی (۱۴۴۰) هستند تغییر می‌کنند؛ مقدار دلخواه ادمین حفظ می‌شود
    op.execute(
        "UPDATE system_settings SET access_token_expire_minutes = 20 "
        "WHERE access_token_expire_minutes = 1440"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "UPDATE system_settings SET access_token_expire_minutes = 1440 "
        "WHERE access_token_expire_minutes = 20"
    )
    op.alter_column('system_settings', 'access_token_expire_minutes', server_default=None)
