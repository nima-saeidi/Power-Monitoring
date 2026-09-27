from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f1b8d4e6a9c3'
down_revision: Union[str, Sequence[str], None] = 'e7a3c9d2f4b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

notification_type = postgresql.ENUM('INFO', 'WARNING', 'ERROR', 'SUCCESS', 'ALERT',
                                    name='notificationtype', create_type=False)
notification_priority = postgresql.ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL',
                                        name='notificationpriority', create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    notification_type.create(bind, checkfirst=True)
    notification_priority.create(bind, checkfirst=True)
    existing = set(sa.inspect(bind).get_table_names())

    if 'notifications' not in existing:
        op.create_table(
            'notifications',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('type', notification_type, nullable=False),
            sa.Column('priority', notification_priority, nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('source_type', sa.String(length=50), nullable=True),
            sa.Column('source_id', sa.Integer(), nullable=True),
            sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('is_read', sa.Boolean(), nullable=False),
            sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('is_dismissed', sa.Boolean(), nullable=False),
            sa.Column('dismissed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('action_url', sa.String(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        )
        for column in ('id', 'user_id', 'source_type', 'is_read', 'created_at', 'expires_at'):
            op.create_index(op.f(f'ix_notifications_{column}'), 'notifications', [column])

    if 'notification_templates' not in existing:
        op.create_table(
            'notification_templates',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('type', notification_type, nullable=False),
            sa.Column('priority', notification_priority, nullable=False),
            sa.Column('title_template', sa.String(length=255), nullable=False),
            sa.Column('message_template', sa.Text(), nullable=False),
            sa.Column('variables', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(op.f('ix_notification_templates_id'), 'notification_templates', ['id'])
        op.create_index(op.f('ix_notification_templates_name'), 'notification_templates', ['name'], unique=True)

    if 'notification_preferences' not in existing:
        op.create_table(
            'notification_preferences',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'),
                      nullable=False, unique=True),
            sa.Column('enable_info', sa.Boolean(), nullable=False),
            sa.Column('enable_warning', sa.Boolean(), nullable=False),
            sa.Column('enable_error', sa.Boolean(), nullable=False),
            sa.Column('enable_success', sa.Boolean(), nullable=False),
            sa.Column('enable_alert', sa.Boolean(), nullable=False),
            sa.Column('min_priority', notification_priority, nullable=False),
            sa.Column('auto_dismiss_after_read', sa.Boolean(), nullable=False),
            sa.Column('auto_dismiss_delay_minutes', sa.Integer(), nullable=True),
            sa.Column('max_display_count', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(op.f('ix_notification_preferences_id'), 'notification_preferences', ['id'])


def downgrade() -> None:
    op.drop_table('notification_preferences')
    op.drop_table('notification_templates')
    op.drop_table('notifications')
    notification_priority.drop(op.get_bind(), checkfirst=True)
    notification_type.drop(op.get_bind(), checkfirst=True)
