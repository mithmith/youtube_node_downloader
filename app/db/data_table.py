from datetime import datetime
from typing import List, Optional

from sqlalchemy import ARRAY, Column, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, Relationship

from app.db.base import Base


class VideoTag(Base, table=True):
    video_id: UUID = Field(sa_column=Column(UUID(as_uuid=True), ForeignKey("videos.id"), primary_key=True))
    tag_id: int = Field(sa_column=Column(Integer, ForeignKey("tags.id"), primary_key=True))

    class Config:
        orm_mode = True


class Channel(Base, table=True):
    __tablename__ = "channels"
    channel_id: str = Field(nullable=False, primary_key=True)
    id: str = Field(nullable=False, unique=True)
    channel: str = Field(nullable=False)
    title: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    channel_url: str = Field(nullable=False, unique=True)
    channel_follower_count: Optional[int] = Field(default=None)
    tags: List[str] = Field(default=[], sa_column=Column(ARRAY(String)))
    thumbnails: List["Thumbnail"] = Relationship(back_populates="channel")
    banner_path: Optional[str] = Field(default=None)
    avatar_path: Optional[str] = Field(default=None)
    videos: List["Video"] = Relationship(back_populates="channel")

    class Config:
        orm_mode = True


class Video(Base, table=True):
    __tablename__ = "videos"
    id: Optional[UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        )
    )
    video_id: str = Field(nullable=False, unique=True)
    channel_id: str = Field(foreign_key="channels.channel_id")
    url: Optional[str] = Field(default=None)
    title: str = Field(nullable=False)
    description: Optional[str] = Field(default=None)
    duration: int = Field(nullable=False)
    view_count: Optional[int] = Field(default=None)
    like_count: Optional[int] = Field(default=0)
    upload_date: Optional[datetime] = Field(default=None)
    video_path: Optional[str] = Field(default=None)
    is_downloaded: bool = Field(default=False)
    channel: Channel = Relationship(back_populates="videos")
    thumbnails: List["Thumbnail"] = Relationship(back_populates="video")
    tags: List["Tag"] = Relationship(back_populates="videos", link_model=VideoTag)

    @property
    def thumbnail_url(self) -> str:
        if not self.thumbnails:
            return ""
        # Находим миниатюру с максимальным суммарным разрешением (ширина + высота)
        max_resolution_thumbnail = max(self.thumbnails, key=lambda t: t.width + t.height)
        return max_resolution_thumbnail.url

    class Config:
        arbitrary_types_allowed = True  # Разрешаем использование произвольных типов
        orm_mode = True


class Tag(Base, table=True):
    __tablename__ = "tags"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, unique=True)
    videos: List[Video] = Relationship(back_populates="tags", link_model=VideoTag)

    class Config:
        orm_mode = True


class Thumbnail(Base, table=True):
    __tablename__ = "thumbnails"
    id: Optional[UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        )
    )
    video_id: Optional[UUID] = Field(
        default=None, sa_column=Column(UUID(as_uuid=True), ForeignKey("videos.id"), nullable=True)
    )
    channel_id: Optional[str] = Field(foreign_key="channels.channel_id", nullable=True)
    url: str = Field(nullable=False)
    width: Optional[int] = Field(nullable=True)
    height: Optional[int] = Field(nullable=True)
    thumbnail_id: Optional[str] = Field(nullable=True)
    thumbnail_path: Optional[str] = Field(default=None)
    video: Video = Relationship(back_populates="thumbnails")
    channel: Channel = Relationship(back_populates="thumbnails")

    __table_args__ = (UniqueConstraint("url", name="uix_thumbnail_url"),)

    class Config:
        orm_mode = True
