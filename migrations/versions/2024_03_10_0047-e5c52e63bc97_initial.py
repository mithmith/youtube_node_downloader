"""Initial

Revision ID: e5c52e63bc97
Revises: 
Create Date: 2025-01-10 00:47:05.109880

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import text

from app.config import settings

# revision identifiers, used by Alembic.
revision: str = "e5c52e63bc97"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создание схемы, если она еще не существует
    op.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.db_schema}"))
    op.create_table(
        "channels",
        sa.Column("channel_id", sa.String(), nullable=False),
        sa.Column(
            "id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("customUrl", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("channel_url", sa.String(), nullable=False),
        sa.Column("channel_follower_count", sa.Integer(), nullable=True),
        sa.Column("viewCount", sa.Integer(), nullable=True),
        sa.Column("videoCount", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=False),
        sa.Column("country", sa.String(255), nullable=True, server_default=""),
        sa.Column("tags", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("banner_path", sa.String(), nullable=True),
        sa.Column("avatar_path", sa.String(), nullable=True),
        sa.Column("last_update", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.Column("list_name", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("channel_id"),
        sa.UniqueConstraint("channel_url", name="channels_channel_url_key"),
        sa.UniqueConstraint("id", name="channels_id_key"),
        schema=settings.db_schema,
    )
    op.create_table(
        "channel_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.String(), nullable=False),
        sa.Column("follower_count", sa.Integer(), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=True),
        sa.Column("video_count", sa.Integer(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["channel_id"], [f"{settings.db_schema}.channels.channel_id"], name="channel_history_channel_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="channel_history_pkey"),
        schema=settings.db_schema,
    )
    op.create_table(
        "videos",
        sa.Column(
            "id", sa.dialects.postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("video_id", sa.String(), nullable=False),
        sa.Column("channel_id", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=False),
        sa.Column("view_count", sa.BigInteger(), nullable=True),
        sa.Column("upload_date", sa.DateTime(), nullable=True),
        sa.Column("like_count", sa.BigInteger(), nullable=True, server_default="0"),
        sa.Column("defaultaudiolanguage", sa.String(), nullable=True),
        sa.Column("comment_count", sa.BigInteger(), nullable=True, server_default="0"),
        sa.Column("last_update", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["channel_id"], [f"{settings.db_schema}.channels.channel_id"], name="videos_channel_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="videos_pkey"),
        sa.UniqueConstraint("video_id", name="videos_video_id_key"),
        schema=settings.db_schema,
    )

    op.create_index("videos_channel_id_idx", "videos", ["channel_id"], schema=settings.db_schema)
    op.create_table(
        "video_history",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("video_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("view_count", sa.BigInteger(), nullable=True),
        sa.Column("like_count", sa.BigInteger(), nullable=True),
        sa.Column("comment_count", sa.BigInteger(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["video_id"], [f"{settings.db_schema}.videos.id"], name="video_history_video_id_fkey"),
        sa.PrimaryKeyConstraint("id", name="video_history_pkey"),
        schema=settings.db_schema,
    )

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="tags_pkey"),
        sa.UniqueConstraint("name", name="tags_name_key"),
        schema=settings.db_schema,
    )
    op.create_table(
        "videotag",
        sa.Column("video_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["video_id"],
            [f"{settings.db_schema}.videos.id"],
            name="videotag_video_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            [f"{settings.db_schema}.tags.id"],
            name="videotag_tag_id_fkey",
        ),
        sa.PrimaryKeyConstraint("video_id", "tag_id", name="videotag_pkey"),
        schema=settings.db_schema,
    )
    op.create_table(
        "thumbnails",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("video_id", sa.UUID(), nullable=True),
        sa.Column("channel_id", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("thumbnail_id", sa.String(), nullable=True),
        sa.Column("thumbnail_path", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            [f"{settings.db_schema}.channels.channel_id"],
            name="thumbnails_channel_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["video_id"],
            [f"{settings.db_schema}.videos.id"],
            name="thumbnails_video_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id", name="thumbnails_pkey"),
        sa.UniqueConstraint("url", name="uix_thumbnail_url"),
        schema=settings.db_schema,
    )
    op.create_table(
        "video_formats",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column("format_id", sa.String(), nullable=False),
        sa.Column("ext", sa.String(), nullable=False),
        sa.Column("resolution", sa.String(), nullable=True),
        sa.Column("fps", sa.Float(), nullable=True),
        sa.Column("audio_channels", sa.Integer(), nullable=True),
        sa.Column("filesize", sa.BigInteger(), nullable=True),
        sa.Column("tbr", sa.Float(), nullable=True),
        sa.Column("protocol", sa.String(), nullable=True),
        sa.Column("vcodec", sa.String(), nullable=True),
        sa.Column("acodec", sa.String(), nullable=True),
        sa.Column("asr", sa.Integer(), nullable=True),
        sa.Column("format", sa.String(), nullable=True),
        sa.Column("format_note", sa.String(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("dynamic_range", sa.String(), nullable=True),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("quality", sa.Float(), nullable=True, server_default="0"),
        sa.Column("has_drm", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("filesize_approx", sa.BigInteger(), nullable=True),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("is_downloaded", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "video_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey(f"{settings.db_schema}.videos.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id", name="video_formats_pkey"),
        schema=settings.db_schema,
    )
    op.create_index("video_formats_video_id_idx", "video_formats", ["video_id"], schema=settings.db_schema)
    # ### end Alembic commands ###


def downgrade() -> None:
    # Удаляем таблицы в обратном порядке создания
    op.drop_table("video_formats", schema=settings.db_schema)
    op.drop_table("thumbnails", schema=settings.db_schema)
    op.drop_table("videotag", schema=settings.db_schema)
    op.drop_table("tags", schema=settings.db_schema)
    op.drop_table("video_history", schema=settings.db_schema)
    op.drop_table("videos", schema=settings.db_schema)
    op.drop_table("channel_history", schema=settings.db_schema)
    op.drop_table("channels", schema=settings.db_schema)
