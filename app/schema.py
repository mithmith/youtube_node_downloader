from typing import Optional

from pydantic import BaseModel


class ThumbnailSchema(BaseModel):
    url: str
    height: Optional[int] = 0
    width: Optional[int] = 0
    preference: Optional[int] = None
    id: Optional[str] = ""
    resolution: Optional[str] = None


class VideoSchema(BaseModel):
    _type: str
    ie_key: Optional[str] = ""
    id: str
    url: Optional[str] = None
    title: str
    tags: list[str] = []
    description: Optional[str] = None
    duration: Optional[int] = None
    thumbnails: list[ThumbnailSchema] = []
    view_count: Optional[int] = None
    timestamp: Optional[int] = None
    release_timestamp: Optional[int] = None
    availability: Optional[str] = None
    live_status: Optional[str] = None
    channel_is_verified: Optional[bool] = None

    class Config:
        arbitrary_types_allowed = True  # Разрешаем использование произвольных типов


class ChannelInfoSchema(BaseModel):
    id: str
    channel: str
    channel_id: str
    title: str
    availability: Optional[str] = None
    channel_follower_count: Optional[int] = None
    description: Optional[str] = None
    tags: list[str]
    thumbnails: list[ThumbnailSchema]
    uploader_id: str
    uploader_url: str
    modified_date: Optional[str] = None
    view_count: Optional[int] = None
    playlist_count: Optional[int] = None
    uploader: str
    channel_url: str
    _type: str
    entries: list[VideoSchema]
    extractor_key: str
    extractor: str
    webpage_url: str
    original_url: Optional[str] = None
    webpage_url_basename: Optional[str] = None
    webpage_url_domain: Optional[str] = None
    release_year: Optional[int] = None


class YTFormatSchema(BaseModel):
    format_id: str
    ext: str
    resolution: str
    fps: Optional[float] = None
    audio_channels: Optional[int] = None
    filesize: Optional[int] = None
    tbr: Optional[float] = None
    protocol: Optional[str] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    asr: Optional[int] = None  # Audio sample rate
    format: Optional[str] = None
    format_note: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    aspect_ratio: Optional[float] = None
    dynamic_range: Optional[str] = None
    language: Optional[str] = None
    quality: Optional[int] = 0
    has_drm: Optional[bool] = False
    filesize_approx: Optional[int] = None  # Приблизительный размер файла
