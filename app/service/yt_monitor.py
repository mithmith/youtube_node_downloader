from time import sleep
from typing import Optional

from loguru import logger

from app.db.data_table import Channel, Thumbnail, Video
from app.db.repository import YoutubeDataRepository
from app.db.base import Session
from app.integrations.ytapi import YTApiClient
from app.integrations.ytdlp import YTChannelDownloader
from app.schema import ChannelAPIInfoSchema, ChannelInfoSchema, VideoSchema


class YTMonitorService:
    def __init__(self, channels_list: list[str], timeout: int = 600) -> None:
        self._channels_list = channels_list
        self._api_client: YTApiClient
        self._yt_dlp_client: YTChannelDownloader
        self._repository = YoutubeDataRepository(session=Session())
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

            # Получаем информацию о канале через yt-dlp
            ytdlp_channel_info: Optional[ChannelInfoSchema] = self._yt_dlp_client.get_channel_info()

            if not ytdlp_channel_info:
                logger.error(f"Failed to retrieve channel info for {channel_url}. Skipping...")
                continue

            # Получаем информацию о канале через YouTube API
            try:
                ytapi_channels_info: list[ChannelAPIInfoSchema] = self._api_client.get_channel_info(
                    [ytdlp_channel_info.channel_id]
                )
            except Exception as e:
                logger.error(f"Error retrieving channel info from YouTube API for {channel_url}: {e}")
                continue

            if not ytapi_channels_info:
                logger.error(f"No channel info returned by YouTube API for {channel_url}. Skipping...")
                continue

            channel_info: Channel = self._combine_channel_info(ytdlp_channel_info, ytapi_channels_info[0])

            # Получаем список видео
            try:
                video_list, channel_id = self._yt_dlp_client.get_video_list()
            except Exception as e:
                logger.error(f"Error retrieving video list for {channel_url}: {e}")
                continue

            # Дополняем данные о видео через YouTube API
            try:
                video_ids = [video.id for video in video_list]
                api_videos_info = self._api_client.get_video_info(video_ids)
            except Exception as e:
                logger.error(f"Error retrieving video info from YouTube API for {channel_url}: {e}")
                api_videos_info = []
                exit()

            # Объединяем данные о видео из yt-dlp и API
            complete_video_list = self._combine_video_info(video_list, api_videos_info)

            # Фильтруем видео на новые и старые
            new_videos, old_videos = self._yt_dlp_client.filter_new_old(complete_video_list, channel_id)

            # Обрабатываем информацию о канале и видео
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

    def _process_channel_info(self, channel_info: ChannelInfoSchema) -> None:
        """
        Processes the channel information:
        Adds new channel to the database if it does not exist and logs the historical data.
        """
        existing_channel = self._repository.get_channel_by_id(channel_info.channel_id)
        if not existing_channel:
            self._repository.add_channel(channel_info)
        self._repository.add_channel_history(channel_info)

    def _combine_video_info(self, yt_dlp_videos: list[VideoSchema], api_videos: list[VideoSchema]) -> list[VideoSchema]:
        """Combine video data from yt-dlp and YouTube API."""
        api_videos_dict = {video.id: video for video in api_videos}
        
        complete_videos = []
        for yt_video in yt_dlp_videos:
            api_video = api_videos_dict.get(yt_video.id)
            if api_video:
                # Объединяем данные из yt-dlp и API
                complete_video = VideoSchema(
                    **yt_video.model_dump(),
                    commentCount=api_video.commentCount or yt_video.commentCount,
                    view_count=api_video.view_count or yt_video.view_count,
                    defaultAudioLanguage=api_video.defaultAudioLanguage or yt_video.defaultAudioLanguage,
                    description=api_video.description or yt_video.description,
                    tags=api_video.tags or yt_video.tags,
                )
            else:
                # Используем только данные из yt-dlp, если API не возвращает данные
                complete_video = yt_video
            complete_videos.append(complete_video)
        return complete_videos

    def _process_new_videos(self, new_videos: list[VideoSchema], channel_id: str) -> None:
        """
        Processes new videos:
        Adds each new video to the database and logs the historical data.
        """
        for video_schema in new_videos:
            video: Video = Video(id=video_schema.id)
            self._repository.add_video(video_schema, channel_id)
            self._repository.add_video_history(video)

    def _process_old_videos(self, old_videos: list[VideoSchema], channel_id: str) -> None:
        """
        Processes old videos:
        Logs the historical data for each video already present in the database.
        """
        for video_schema in old_videos:
            video: Video = self._repository.get_video_by_id(youtube_video_id=video_schema.id)
            self._repository.add_video_history(video)
