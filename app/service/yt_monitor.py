from time import sleep

from loguru import logger

from app.db.data_table import Channel, Thumbnail, Video
from app.db.repository import YoutubeDataRepository
from app.integrations.ytapi import YTApiClient
from app.integrations.ytdlp import YTChannelDownloader
from app.schema import ChannelAPIInfoSchema, ChannelInfoSchema, VideoSchema


class YTMonitorService:
    def __init__(self, channels_list: list[str], timeout: int = 300) -> None:
        self._channels_list = channels_list
        self._api_client: YTApiClient
        self._yt_dlp_client: YTChannelDownloader
        self._repository = YoutubeDataRepository()
        self._timeout = timeout

    def run(self):
        while True:
            self.monitor_channels_for_newold_videos()
            sleep(self._timeout)

    def monitor_channels_for_newold_videos(self) -> None:
        for channel_url in self._channels_list:
            logger.info(f"Getting video from: {channel_url}")
            self._yt_dlp_client = YTChannelDownloader(channel_url)
            self._api_client = YTApiClient()

            # Получаем список видео и id канала
            ytdlp_channel_info: ChannelInfoSchema = self._yt_dlp_client.get_channel_info()
            ytapi_channels_info: ChannelAPIInfoSchema = self._api_client.get_channel_info(
                [ytdlp_channel_info.channel_id]
            )
            channel_info: Channel = self._combine_channel_info(ytdlp_channel_info, ytapi_channels_info[0])
            video_list, channel_id = self._yt_dlp_client.get_video_list()
            new_videos, old_videos = self._yt_dlp_client.filter_new_old(video_list, channel_id)

            if channel_info:
                self._process_channel_info(channel_info)
            if new_videos:
                self._process_new_videos(new_videos, channel_id)
            if old_videos:
                self._process_old_videos(old_videos, channel_id)

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

    def _process_channel_info(self, channel_info):
        existing_channel = self._repository.get_channel_by_id(channel_info.channel_id)
        if not existing_channel:
            self._repository.add_channel(channel_info)
        self._repository.add_channel_history(channel_info)

    def _process_new_videos(self, new_videos, channel_id):
        for video in new_videos:
            self._repository.add_video(video)
            self._repository.add_video_history(video, channel_id)

    def _process_old_videos(self, old_videos, channel_id):
        for video in old_videos:
            self._repository.add_video_history(video, channel_id)
            