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
        self._repository = YoutubeDataRepository(session=Session())

    def get_channel_list(self, channel_url: str) -> tuple[list[VideoSchema], str]:
        result = subprocess.run(
            ["yt-dlp", "-J", "--flat-playlist", "--quiet", "--no-warnings", "--no-progress", channel_url],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error(f"Ошибка при выполнении yt-dlp для {channel_url}: {result.stderr}")
            return []

        video_list: list[VideoSchema] = []
        try:
            data = json.loads(result.stdout)
            # Проверяем, является ли первый элемент в entries плейлистом
            if data.get("entries") and data["entries"][0].get("_type") == "playlist":
                # Обрабатываем каждый плейлист отдельно
                for playlist_data in data["entries"]:
                    videos, channel_id = self.process_playlist(playlist_data)
                    video_list.extend(videos)
            else:
                # Обрабатываем как одиночный плейлист
                video_list, channel_id = self.process_playlist(data)
        except json.JSONDecodeError:
            logger.error(f"Не удалось декодировать JSON из вывода yt-dlp для {channel_url}")
            return []
        except KeyError:
            logger.error(f"Отсутствует ключевая информация в данных от {channel_url}")
            return []
        return video_list, channel_id

    def update_channels_metadata(self, channels_list: list[str]) -> None:
        for channel_url in channels_list:
            videos, channel_id = self.get_channel_list(channel_url)
            for v in videos:
                self._repository.add_video_metadata(v, channel_id)

    def process_playlist(self, playlist_data: dict) -> tuple[list[VideoSchema], str]:
        try:
            channel_data = ChannelInfoSchema(**playlist_data)
            self._repository.add_or_update_channel(channel_data)
            return channel_data.entries, channel_data.channel_id
        except ValidationError as e:
            logger.error(f"Ошибка валидации данных: {e}")
            return []

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

    def _construct_video_path(self, video_id: str) -> Path:
        return Path(settings.video_download_path) / f"{video_id}.mp4"

    def _construct_thumbnail_path(self, video_id: str) -> Path:
        return Path(settings.thumbnail_download_path) / f"{video_id}.jpg"
