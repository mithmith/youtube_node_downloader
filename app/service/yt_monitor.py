import asyncio
from multiprocessing import Process, Queue
from typing import Optional

from loguru import logger

from app.db.base import Session
from app.db.data_table import Channel, ChannelHistory, Thumbnail
from app.db.repository import YoutubeDataRepository
from app.integrations.ytapi import YTApiClient
from app.integrations.ytdlp import YTChannelDownloader
from app.schema import ChannelAPIInfoSchema, ChannelInfoSchema, NewVideoSchema, VideoSchema


class YTMonitorService:
    def __init__(
        self,
        channels_list: list[str],
        new_videos_timeout: int = 600,
        history_timeout: int = 9999,
        new_videos_queue: Optional[Queue] = None,
    ) -> None:
        self._channels_list = channels_list
        self._new_videos_timeout = new_videos_timeout
        self._history_timeout = history_timeout
        self._queue = new_videos_queue  # Очередь для обработки новых видео

    def run(self, monitor_new: bool = True, monitor_history: bool = True) -> list[Process]:
        """Запускает процессы мониторинга новых видео и истории каналов."""
        processes: list[Process] = []

        if monitor_new:
            new_videos_process = Process(target=self._start_async_loop, args=(self._monitor_new_videos,))
            processes.append(new_videos_process)
            new_videos_process.start()

        if monitor_history:
            history_process = Process(target=self._start_async_loop, args=(self._monitor_channel_videos_history,))
            processes.append(history_process)
            history_process.start()

        return processes

    def _start_async_loop(self, coro_func, *args, **kwargs):
        """Запускает событийный цикл для асинхронной функции."""
        asyncio.run(coro_func(*args, **kwargs))

    async def _monitor_new_videos(self):
        """Мониторинг новых видео с заданным интервалом."""
        while True:
            logger.info("Starting new video monitoring...")
            for i, channel_url in enumerate(self._channels_list):
                logger.info(f"[{i+1}/{len(self._channels_list)}] Processing new videos for channel: {channel_url}")
                try:
                    await self._process_channel_videos(channel_url, process_new=True)
                except Exception as e:
                    logger.error(f"Error monitoring new videos for {channel_url}: {e}")
                await asyncio.sleep(2)
            logger.info(f"Waiting for {self._new_videos_timeout} seconds")
            await asyncio.sleep(self._new_videos_timeout)

    async def _monitor_channel_videos_history(self):
        """Мониторинг истории каналов с заданным интервалом."""
        await asyncio.sleep(10)
        while True:
            logger.info("Starting channel history monitoring...")
            for i, channel_url in enumerate(self._channels_list):
                logger.info(f"[{i+1}/{len(self._channels_list)}] Processing channel history for: {channel_url}")
                try:
                    await self._process_channel_videos(channel_url, process_old=True)
                except Exception as e:
                    logger.error(f"Error updating channel history for {channel_url}: {e}")
                await asyncio.sleep(2)
            logger.info(f"Waiting for {self._history_timeout} seconds")
            await asyncio.sleep(self._history_timeout)

    async def _process_channel_videos(self, channel_url: str, process_new: bool = False, process_old: bool = False):
        """Обработка новых и старых видео для канала."""
        yt_dlp_client = YTChannelDownloader(channel_url)
        api_client = YTApiClient()

        # Получение информации о канале через yt-dlp
        ytdlp_channel_info: Optional[ChannelInfoSchema] = yt_dlp_client.get_channel_info()

        if not ytdlp_channel_info:
            logger.error(f"Failed to retrieve channel info for {channel_url}. Skipping...")
            return

        # Если канала нет в БД, до дополняем о нём информацию через API и добавляем в БД
        if not yt_dlp_client.channel_exist(ytdlp_channel_info.channel_id):
            logger.debug("Channel not found in database! Updating...")
            # Получение информации о канале через API
            ytapi_channel_info: list[ChannelAPIInfoSchema] = api_client.get_channel_info(
                [ytdlp_channel_info.channel_id]
            )

            if len(ytapi_channel_info) == 0:
                logger.error(f"No channel info returned by YouTube API for {channel_url}. Skipping...")
                return

            # Объединение и обработка информации о канале
            full_channel_info = self._combine_channel_info(ytdlp_channel_info, ytapi_channel_info[0])
            self._process_channel_info(full_channel_info, add_history=process_old)
        elif process_old:
            ytapi_channel_info = api_client.get_channel_info([ytdlp_channel_info.channel_id])
            if len(ytapi_channel_info):
                self._process_channel_history(
                    ChannelHistory(
                        channel_id=ytdlp_channel_info.channel_id,
                        follower_count=ytdlp_channel_info.channel_follower_count,
                        view_count=ytapi_channel_info[0].viewCount,
                        video_count=ytapi_channel_info[0].videoCount,
                    )
                )
            else:
                logger.warning(f"No channel info returned by YouTube API for {channel_url}.")

        # Получение списка видео через yt-dlp
        video_list, channel_id = yt_dlp_client.get_video_list()
        # Фильтруем видео на новые и старые
        new_videos, old_videos = yt_dlp_client.filter_new_old(video_list, channel_id)
        logger.debug(f"Videos count: {len(video_list)}, New: {len(new_videos)}, Old: {len(old_videos)}")

        # Определяем, какие видео нужно обрабатывать
        videos_to_process: list[VideoSchema] = []
        if process_new and process_old:
            videos_to_process = video_list
        elif process_new:
            videos_to_process = new_videos
        elif process_old:
            videos_to_process = old_videos

        # Получение дополнительной информации о видео через YouTube API
        try:
            video_ids = [video.id for video in videos_to_process]
            api_videos_info = api_client.get_video_info_list(video_ids)
        except Exception as e:
            logger.error(f"Error retrieving video info from YouTube API for {channel_url}: {e}")
            return

        # Объединение данных о видео
        complete_video_list = self._combine_video_info(videos_to_process, api_videos_info)
        new_videos, old_videos = yt_dlp_client.filter_new_old(complete_video_list, channel_id)
        logger.debug(
            f"Total combined videos: {len(complete_video_list)}, New: {len(new_videos)}, Old: {len(old_videos)}"
        )

        if process_new and new_videos:
            yt_dlp_client.update_video_formats()
            self._process_new_videos(new_videos, channel_id)

            if self._queue is not None:
                for video in new_videos:
                    if video.url.find("shorts") == -1:  # исключаем пока шортсы из публикации
                        self._queue.put(
                            NewVideoSchema(
                                channel_name=ytdlp_channel_info.channel,
                                channel_url=ytdlp_channel_info.channel_url,
                                video_title=video.title,
                                video_url=video.url,
                            )
                        )  # add video to queue for telegram bot
        if process_old and old_videos:
            self._process_old_videos(old_videos)

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

    def _process_channel_info(self, channel_info: ChannelInfoSchema, add_history: bool) -> None:
        """
        Processes the channel information:
        Updates or adds a channel to the database and optionally logs the historical data.
        """
        with Session() as session:
            repository = YoutubeDataRepository(session)
            channel = repository.upsert_channel(channel_info)
            if add_history:
                repository.add_channel_history(channel)

    def _process_channel_history(self, history: ChannelHistory):
        """Add a channel history into database"""
        with Session() as session:
            YoutubeDataRepository(session).add_channel_history(history)

    def _combine_video_info(self, yt_dlp_videos: list[VideoSchema], api_videos: list[VideoSchema]) -> list[VideoSchema]:
        """Combine video data from yt-dlp and YouTube API."""
        api_videos_dict = {video.id: video for video in api_videos}

        complete_videos = []
        for yt_dlp_video in yt_dlp_videos:
            yt_api_video = api_videos_dict.get(yt_dlp_video.id)
            if yt_api_video:
                # Объединяем данные из yt-dlp и API
                complete_video = VideoSchema(
                    ie_key=yt_dlp_video.ie_key,  # Используем данные yt-dlp
                    id=yt_dlp_video.id,
                    url=yt_dlp_video.url or yt_api_video.url,
                    title=yt_dlp_video.title or yt_api_video.title,
                    description=yt_api_video.description,
                    tags=yt_dlp_video.tags + yt_api_video.tags,
                    duration=yt_dlp_video.duration or yt_api_video.duration,
                    thumbnails=yt_dlp_video.thumbnails + yt_api_video.thumbnails,
                    view_count=yt_api_video.view_count,  # Предпочитаем данные API для точности
                    like_count=yt_api_video.like_count,
                    commentCount=yt_api_video.commentCount,  # Берем из API
                    timestamp=yt_dlp_video.timestamp or yt_api_video.timestamp,
                    release_timestamp=yt_dlp_video.release_timestamp,  # Данные из yt-dlp
                    availability=yt_api_video.availability,  # Берем из API
                    live_status=yt_api_video.live_status,  # Берем из API
                    channel_is_verified=yt_api_video.channel_is_verified,  # Берем из API
                    defaultAudioLanguage=yt_api_video.defaultAudioLanguage,
                )
            else:
                # Используем только данные из yt-dlp, если API не возвращает данные
                complete_video = yt_dlp_video
            complete_videos.append(complete_video)
        return complete_videos

    def _process_new_videos(self, new_videos: list[VideoSchema], channel_id: str) -> None:
        """
        Processes new videos:
        Adds each new video to the database and logs the historical data.
        """
        with Session() as session:
            repository = YoutubeDataRepository(session)
            for video_schema in new_videos:
                try:
                    # Добавляем видео в базу данных
                    repository.add_video(video_schema, channel_id)
                    # Добавляем исторические данные о видео
                    repository.add_video_history(video_schema)
                    logger.info(f"Added new video: {video_schema.title} (ID: {video_schema.id})")
                except Exception as e:
                    logger.error(f"Failed to process video {video_schema.id}: {e}")
                    continue

    def _process_old_videos(self, old_videos: list[VideoSchema]) -> None:
        """
        Processes old videos:
        Logs the historical data for each video already present in the database.
        """
        with Session() as session:
            repository = YoutubeDataRepository(session)
            for video_schema in old_videos:
                repository.update_video(video_schema)
                repository.add_video_history(video_schema)
