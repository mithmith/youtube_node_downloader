import json
import subprocess
from pathlib import Path

import httpx
from loguru import logger
from pydantic import ValidationError

from app.config import settings
from app.db.base import Session
from app.db.data_table import Video
from app.db.repository import YoutubeDataRepository
from app.schema import ChannelInfoSchema, VideoSchema, YTFormatSchema


class YTDownloader:
    def __init__(self):
        self._channel_data = {}
        self._repository = YoutubeDataRepository(session=Session())

    def get_channel_info(self, channel_url: str) -> ChannelInfoSchema:
        if not self._channel_data:
            self._channel_data = self._get_channel_data(channel_url)
        if self._channel_data:
            try:
                channel_info = ChannelInfoSchema(**self._channel_data)
                # self._repository.add_or_update_channel(channel_info)
                return channel_info
            except Exception as e:
                logger.error("Ошибка при обработке информации о канале:", exc_info=e)
        return None

    def get_video_list(self, channel_url: str) -> tuple[list[VideoSchema], str]:
        if not self._channel_data:
            self._channel_data = self._get_channel_data(channel_url)
        video_list = []
        channel_id = ""
        if self._channel_data:
            try:
                video_list, channel_id = self._extract_video_list()
                # Можно добавить логику сохранения списка видео в базу данных здесь, если требуется
            except Exception as e:
                logger.error("Ошибка при обработке списка видео:", exc_info=e)
        return video_list, channel_id

    def _get_channel_data(self, channel_url: str) -> dict:
        result = subprocess.run(
            ["yt-dlp", "-J", "--flat-playlist", "--quiet", "--no-warnings", "--no-progress", channel_url],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error(f"Ошибка при выполнении yt-dlp для {channel_url}: {result.stderr}")
            return {}

        try:
            data = json.loads(result.stdout)
            return data
        except json.JSONDecodeError:
            logger.error(f"Не удалось декодировать JSON из вывода yt-dlp для {channel_url}")
        except KeyError:
            logger.error(f"Отсутствует ключевая информация в данных от {channel_url}")
        return {}

    def _extract_video_list(self) -> tuple[list[VideoSchema], str]:
        video_list = []
        channel_id = self._channel_data.get("channel_id", "")
        if "entries" in self._channel_data:
            for entry in self._channel_data["entries"]:
                if entry.get("_type") == "playlist":
                    video_list.extend([VideoSchema(**video) for video in entry.get("entries", [])])
                else:
                    video_list.append(VideoSchema(**entry))
        return video_list, channel_id

    def update_channels_metadata(self, channels_list: list[str]) -> None:
        for channel_url in channels_list:
            videos, channel_id = self.get_channelvideo_list(channel_url)
            for v in videos:
                self._repository.add_video_metadata(v, channel_id)

    def download_video(self, video_id: str, format: str = "bv+ba/b") -> None:
        video: Video = self._repository.get_video(video_id)
        if video:
            video_path = self._construct_video_path(video_id)
            command = f'yt-dlp -f "{format}" -o "{video_path}" {video.url}'
            subprocess.run(command, shell=True, check=True)
            self._repository.update_video_path(video_id, video_path)

    def download_thumbnail(self, video_id: str) -> None:
        video: Video = self._repository.get_video(video_id)
        if video and video.thumbnail_url:
            try:
                r = httpx.get(video.thumbnail_url)
                r.raise_for_status()
                thumbnail_path = self._construct_thumbnail_path(video_id)
                thumbnail_path.write_bytes(r.content)
                self._repository.update_thumbnail_path(video_id, video.thumbnail_url, thumbnail_path)
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error occurred: {e}")

    def update_video_formats(self) -> None:
        video_ids = self._repository.get_video_ids_without_formats(limit=50)
        logger.debug(len(video_ids))
        for v_id in video_ids:
            formats = self.get_video_formats(v_id)
            for format_data in formats:
                self._repository.add_video_format(format_data, v_id)

    def get_video_formats(self, video_id: str) -> list[YTFormatSchema] | None:
        result = subprocess.run(
            [
                "yt-dlp",
                "-J",
                "--quiet",
                "--no-warnings",
                "--no-progress",
                f"https://www.youtube.com/watch?v={video_id}",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error(f"Ошибка при выполнении yt-dlp для video_id={video_id}: {result.stderr}")
            return None

        try:
            video_data = json.loads(result.stdout)
            formats_data = video_data.get("formats", [])  # Получаем список форматов
            formats = []
            for format_data in formats_data:
                try:
                    format_schema = YTFormatSchema(**format_data)  # Создаём объект схемы для каждого формата
                    formats.append(format_schema)
                except ValidationError as e:
                    logger.error(f"Ошибка валидации формата видео: {e}")
            return formats
        except json.JSONDecodeError as e:
            logger.error(f"Не удалось декодировать JSON: {e}")
            return None

    def video_exist(self, youtube_video_id: str) -> bool:
        return bool(self._repository.get_video(youtube_video_id))

    def _construct_video_path(self, video_id: str) -> Path:
        return Path(settings.video_download_path) / f"{video_id}.mp4"

    def _construct_thumbnail_path(self, video_id: str) -> Path:
        return Path(settings.thumbnail_download_path) / f"{video_id}.jpg"
