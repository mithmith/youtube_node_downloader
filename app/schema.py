from datetime import datetime
from typing import List, Optional

from dateutil import parser
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
    id: str  # youtube video id
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


class ChannelAPIInfoSchema(BaseModel):
    id: str
    title: str
    description: Optional[str]
    customUrl: Optional[str]
    published_at: datetime
    country: Optional[str]
    viewCount: Optional[int]
    subscriberCount: Optional[int]
    hiddenSubscriberCount: Optional[bool]
    videoCount: Optional[int]
    topicIds: Optional[List[str]]
    topicCategories: Optional[List[str]]
    privacyStatus: Optional[str]
    isLinked: Optional[bool]
    longUploadsStatus: Optional[str]
    madeForKids: Optional[bool]
    selfDeclaredMadeForKids: Optional[bool]

    @classmethod
    def from_api_response(cls, data: dict):
        snippet = data.get("snippet", {})
        statistics = data.get("statistics", {})
        topicDetails = data.get("topicDetails", {})
        status = data.get("status", {})

        # Преобразование строки в datetime
        published_at = parser.isoparse(snippet.get("publishedAt")) if "publishedAt" in snippet else None

        return cls(
            id=data["id"],
            title=snippet.get("title"),
            description=snippet.get("description"),
            customUrl=snippet.get("customUrl"),
            published_at=published_at,
            country=snippet.get("country"),
            viewCount=int(statistics.get("viewCount", 0)) if statistics.get("viewCount") else None,
            subscriberCount=int(statistics.get("subscriberCount", 0)) if statistics.get("subscriberCount") else None,
            hiddenSubscriberCount=statistics.get("hiddenSubscriberCount"),
            videoCount=int(statistics.get("videoCount", 0)) if statistics.get("videoCount") else None,
            topicIds=topicDetails.get("topicIds"),
            topicCategories=topicDetails.get("topicCategories"),
            privacyStatus=status.get("privacyStatus"),
            isLinked=status.get("isLinked"),
            longUploadsStatus=status.get("longUploadsStatus"),
            madeForKids=status.get("madeForKids"),
            selfDeclaredMadeForKids=status.get("selfDeclaredMadeForKids"),
        )


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
