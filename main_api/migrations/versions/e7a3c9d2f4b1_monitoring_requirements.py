from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'e7a3c9d2f4b1'
down_revision: Union[str, Sequence[str], None] = 'd5e8f2a4c1b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('locations', sa.Column('code', sa.String(length=50), nullable=True))
    op.create_index(op.f('ix_locations_code'), 'locations', ['code'], unique=True)

    op.add_column('posts', sa.Column('code', sa.String(length=50), nullable=True))
    op.create_index(op.f('ix_posts_code'), 'posts', ['code'], unique=True)
    op.add_column('posts', sa.Column('post_type', sa.String(length=20), nullable=True))

    op.add_column('feeders', sa.Column('control_register', sa.Integer(), nullable=True))
    op.add_column('feeders', sa.Column('load_status', sa.String(length=20), nullable=False, server_default='unknown'))

    op.add_column('links', sa.Column('feeder_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_links_feeder_id_feeders', 'links', 'feeders', ['feeder_id'], ['id'], ondelete='SET NULL')
    op.add_column('links', sa.Column('load_status', sa.String(length=20), nullable=False, server_default='unknown'))

    op.add_column('users', sa.Column('allowed_pages', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'allowed_pages')
    op.drop_column('links', 'load_status')
    op.drop_constraint('fk_links_feeder_id_feeders', 'links', type_='foreignkey')
    op.drop_column('links', 'feeder_id')
    op.drop_column('feeders', 'load_status')
    op.drop_column('feeders', 'control_register')
    op.drop_column('posts', 'post_type')
    op.drop_index(op.f('ix_posts_code'), table_name='posts')
    op.drop_column('posts', 'code')
    op.drop_index(op.f('ix_locations_code'), table_name='locations')
    op.drop_column('locations', 'code')
