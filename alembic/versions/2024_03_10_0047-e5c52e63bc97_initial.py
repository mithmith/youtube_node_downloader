"""Initial

Revision ID: e5c52e63bc97
Revises: 
Create Date: 2024-03-10 00:47:05.109880

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5c52e63bc97"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "channels",
        sa.Column("channel_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("channel", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("channel_url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("channel_follower_count", sa.Integer(), nullable=True),
        sa.Column("tags", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("banner_path", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("avatar_path", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.PrimaryKeyConstraint("channel_id"),
        sa.UniqueConstraint("channel_url"),
        sa.UniqueConstraint("id"),
        schema="youtube",
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        schema="youtube",
    )
    op.create_table(
        "videos",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("video_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("channel_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=False),
        sa.Column("view_count", sa.Integer(), nullable=True),
        sa.Column("upload_date", sa.DateTime(), nullable=True),
        sa.Column("video_path", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("is_downloaded", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            ["youtube.channels.channel_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id"),
        schema="youtube",
    )
    op.create_table(
        "thumbnails",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("video_id", sa.UUID(), nullable=True),
        sa.Column("channel_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("thumbnail_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("thumbnail_path", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            ["youtube.channels.channel_id"],
        ),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["youtube.videos.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url", name="uix_thumbnail_url"),
        schema="youtube",
    )
    op.create_table(
        "videotag",
        sa.Column("video_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["youtube.tags.id"],
        ),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["youtube.videos.id"],
        ),
        sa.PrimaryKeyConstraint("video_id", "tag_id"),
        schema="youtube",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("videotag", schema="youtube")
    op.drop_table("thumbnails", schema="youtube")
    op.drop_table("videos", schema="youtube")
    op.drop_table("tags", schema="youtube")
    op.drop_table("channels", schema="youtube")
    # ### end Alembic commands ###
