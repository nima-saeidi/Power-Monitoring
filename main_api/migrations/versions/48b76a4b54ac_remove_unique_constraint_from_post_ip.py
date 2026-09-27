from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '48b76a4b54ac'
down_revision: Union[str, Sequence[str], None] = '088d59b31213'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(op.f('posts_ip_address_key'), 'posts', type_='unique')


def downgrade() -> None:
    op.create_unique_constraint(op.f('posts_ip_address_key'), 'posts', ['ip_address'], postgresql_nulls_not_distinct=False)
