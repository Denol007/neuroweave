"""add source_type external_id article_type multi_source

Revision ID: 0ea6ef634004
Revises: 164635a24ce9
Create Date: 2026-02-23 17:35:34.688392

Three-phase migration:
1. Add new columns as NULLABLE
2. Backfill from existing discord_id columns
3. Set NOT NULL + add constraints
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '0ea6ef634004'
down_revision: Union[str, None] = '164635a24ce9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === PHASE 1: Add columns as NULLABLE ===

    # servers
    op.add_column('servers', sa.Column('source_type', sa.String(length=20), nullable=True))
    op.add_column('servers', sa.Column('external_id', sa.String(length=200), nullable=True))
    op.add_column('servers', sa.Column('source_url', sa.Text(), nullable=True))
    op.add_column('servers', sa.Column('source_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # channels
    op.add_column('channels', sa.Column('external_id', sa.String(length=200), nullable=True))

    # messages
    op.add_column('messages', sa.Column('external_id', sa.String(length=200), nullable=True))

    # articles
    op.add_column('articles', sa.Column('article_type', sa.String(length=30), nullable=True))
    op.add_column('articles', sa.Column('source_type', sa.String(length=20), nullable=True))
    op.add_column('articles', sa.Column('source_url', sa.Text(), nullable=True))

    # === PHASE 2: Backfill existing data ===

    op.execute("UPDATE servers SET source_type = 'discord', external_id = discord_id, source_metadata = '{}' WHERE source_type IS NULL")
    op.execute("UPDATE channels SET external_id = discord_id WHERE external_id IS NULL")
    op.execute("UPDATE messages SET external_id = discord_message_id WHERE external_id IS NULL")
    op.execute("UPDATE articles SET article_type = 'troubleshooting', source_type = 'discord' WHERE article_type IS NULL")

    # === PHASE 3: Set NOT NULL + constraints ===

    # servers
    op.alter_column('servers', 'source_type', nullable=False, server_default='discord')
    op.alter_column('servers', 'external_id', nullable=False)
    op.alter_column('servers', 'source_metadata', nullable=False, server_default='{}')
    op.alter_column('servers', 'discord_id', existing_type=sa.VARCHAR(length=32), nullable=True)
    op.create_index(op.f('ix_servers_source_type'), 'servers', ['source_type'], unique=False)
    op.create_index(op.f('ix_servers_external_id'), 'servers', ['external_id'], unique=False)
    op.create_unique_constraint('uq_server_source_external', 'servers', ['source_type', 'external_id'])

    # channels
    op.alter_column('channels', 'external_id', nullable=False)
    op.alter_column('channels', 'discord_id', existing_type=sa.VARCHAR(length=32), nullable=True)
    op.create_index(op.f('ix_channels_external_id'), 'channels', ['external_id'], unique=False)
    op.create_unique_constraint('uq_channel_server_external', 'channels', ['server_id', 'external_id'])

    # messages
    op.alter_column('messages', 'external_id', nullable=False)
    op.alter_column('messages', 'discord_message_id', existing_type=sa.VARCHAR(length=32), nullable=True)
    op.alter_column('messages', 'reply_to_id', existing_type=sa.VARCHAR(length=32), type_=sa.String(length=200), existing_nullable=True)
    op.create_index(op.f('ix_messages_external_id'), 'messages', ['external_id'], unique=False)

    # articles
    op.alter_column('articles', 'article_type', nullable=False, server_default='troubleshooting')
    op.alter_column('articles', 'source_type', nullable=False, server_default='discord')
    op.create_index(op.f('ix_articles_article_type'), 'articles', ['article_type'], unique=False)
    op.create_index(op.f('ix_articles_source_type'), 'articles', ['source_type'], unique=False)


def downgrade() -> None:
    op.drop_constraint('uq_server_source_external', 'servers', type_='unique')
    op.drop_index(op.f('ix_servers_source_type'), table_name='servers')
    op.drop_index(op.f('ix_servers_external_id'), table_name='servers')
    op.alter_column('servers', 'discord_id', existing_type=sa.VARCHAR(length=32), nullable=False)
    op.drop_column('servers', 'source_metadata')
    op.drop_column('servers', 'source_url')
    op.drop_column('servers', 'external_id')
    op.drop_column('servers', 'source_type')

    op.drop_index(op.f('ix_messages_external_id'), table_name='messages')
    op.alter_column('messages', 'reply_to_id', existing_type=sa.String(length=200), type_=sa.VARCHAR(length=32), existing_nullable=True)
    op.alter_column('messages', 'discord_message_id', existing_type=sa.VARCHAR(length=32), nullable=False)
    op.drop_column('messages', 'external_id')

    op.drop_constraint('uq_channel_server_external', 'channels', type_='unique')
    op.drop_index(op.f('ix_channels_external_id'), table_name='channels')
    op.alter_column('channels', 'discord_id', existing_type=sa.VARCHAR(length=32), nullable=False)
    op.drop_column('channels', 'external_id')

    op.drop_index(op.f('ix_articles_source_type'), table_name='articles')
    op.drop_index(op.f('ix_articles_article_type'), table_name='articles')
    op.drop_column('articles', 'source_url')
    op.drop_column('articles', 'source_type')
    op.drop_column('articles', 'article_type')
