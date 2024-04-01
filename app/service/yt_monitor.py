from loguru import logger

from app.db.data_table import Channel, Thumbnail, Video
from app.integrations.ytapi import YTApiClient
from app.integrations.ytdlp import YTChannelDownloader
from app.schema import ChannelAPIInfoSchema, ChannelInfoSchema


class YTMonitorService:
    def __init__(self, channels_list: list[str]) -> None:
        self._channels_list = channels_list
        self._api_client: YTApiClient
        self._yt_dlp_client: YTChannelDownloader

    def monitor_channels_for_new_videos(self) -> list[Video]:
        channels_new_videos: list[Video] = []
        for channel_url in self._channels_list:
            logger.info(f"Getting video from: {channel_url}")
            self._yt_dlp_client = YTChannelDownloader(channel_url)
            # Получаем список видео и id канала
            # ytdlp_channel_info: ChannelInfoSchema = self._yt_dlp_client.get_channel_info()
            video_list, channel_id = self._yt_dlp_client.get_video_list()
            new_videos, old_videos = self._yt_dlp_client.filter_new_old(video_list, channel_id)
            if new_videos:
                channels_new_videos.extend(new_videos)

        return channels_new_videos

    def _combine_channel_info(
        self, ytdlp_channel_info: ChannelInfoSchema, ytapi_channel_info: ChannelAPIInfoSchema
    ) -> Channel:
        combined_channel = Channel(
            channel_id=ytdlp_channel_info.channel_id or ytapi_channel_info.id,
            customUrl=ytapi_channel_info.customUrl,
            title=ytdlp_channel_info.title or ytapi_channel_info.title,
            description=ytdlp_channel_info.description or ytapi_channel_info.description,
            channel_url=ytdlp_channel_info.channel_url,
            channel_follower_count=ytdlp_channel_info.channel_follower_count or ytapi_channel_info.subscriberCount,
            viewCount=ytapi_channel_info.viewCount,
            videoCount=ytapi_channel_info.videoCount,
            published_at=ytapi_channel_info.published_at,
            country=ytapi_channel_info.country,
            tags=ytdlp_channel_info.tags,
            thumbnails=[Thumbnail(**thumb.model_dump()) for thumb in ytdlp_channel_info.thumbnails],
        )
        return combined_channel
