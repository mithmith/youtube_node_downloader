from loguru import logger

from app.db.data_table import Video
from app.integrations.ytapi import YTApiClient
from app.integrations.ytdlp import YTDownloader
from app.schema import VideoSchema


class YTMonitorService:
    def __init__(self) -> None:
        self._api_client = YTApiClient()
        self._yt_dlp_client = YTDownloader()

    def monitor_channels_for_new_videos(self, channels_list: list[str]) -> list[Video]:
        new_videos: list[Video] = []
        for channel_url in channels_list:
            # Получаем список видео и id канала
            channel_videos, channel_id = self._yt_dlp_client.get_channelvideo_list(channel_url)
            for video_schema in channel_videos:
                if not self._yt_dlp_client.video_exist(video_schema.id):
                    # Видео новое, получаем дополнительную информацию с YouTube Data API
                    try:
                        video_info = self._api_client.get_video_info([video_schema.id])
                        if video_info:
                            # Обогащаем информацию о видео и заносим в базу
                            raise
                            enriched_video = self._api_client.update_video_info(video_info)
                            new_videos.append(enriched_video)
                    except Exception as e:
                        logger.error(f"Ошибка при получении информации о видео {video_schema.id}: {e}")

        return new_videos
