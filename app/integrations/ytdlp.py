import asyncio
import json
import subprocess
from pathlib import Path
from typing import Optional
import locale

import httpx
from pydantic import ValidationError

from app.config import logger, settings
from app.db.base import Session
from app.db.data_table import Video
from app.db.repository import YoutubeDataRepository
from app.schema import ChannelInfoSchema, VideoDownloadSchema, VideoSchema, YTFormatSchema


class YTChannelDownloader:
    def __init__(self, channel_url: str):
        self._channel_data = {}
        self._channel_url = channel_url
        self._repository = YoutubeDataRepository(session=Session())

    def get_channel_info(self) -> Optional[ChannelInfoSchema]:
        if not self._channel_data:
            self._channel_data = self._get_channel_data()
        if self._channel_data:
            try:
                return ChannelInfoSchema(**self._channel_data)
            except Exception as e:
                logger.error(f"Ошибка при обработке информации о канале: {e}")
        return None

    def get_video_list(self) -> tuple[list[VideoSchema], str]:
        if not self._channel_data:
            self._channel_data = self._get_channel_data()
        video_list = []
        channel_id = ""
        if self._channel_data:
            try:
                logger.debug("Getting video list from channel data...")
                video_list, channel_id = self._extract_video_list()
            except Exception as e:
                logger.error(f"Ошибка при обработке списка видео: {e}")
        return video_list, channel_id

    def filter_new_old(
        self, video_list: list[VideoSchema], channel_id: str
    ) -> tuple[list[VideoSchema], list[VideoSchema]]:
        v_ids = [v.id for v in video_list]
        new_v_ids, _ = self._repository.get_new_and_existing_video_ids(v_ids, channel_id)
        new_videos = [v for v in video_list if v.id in new_v_ids]
        old_videos = [v for v in video_list if v.id not in new_v_ids]
        return new_videos, old_videos

    def _get_channel_data(self) -> dict:
        command = ["yt-dlp", "-J", "--flat-playlist", "--quiet", "--no-warnings", "--no-progress", self._channel_url]
        logger.debug(f"Executing command: {' '.join(command)}")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error(f"Error while executing yt-dlp for {self._channel_url}: {result.stderr}")
            return {}

        try:
            data = json.loads(result.stdout)
            return data
        except json.JSONDecodeError:
            logger.error(f"Не удалось декодировать JSON из вывода yt-dlp для {self._channel_url}")
        except KeyError:
            logger.error(f"Отсутствует ключевая информация в данных от {self._channel_url}")
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

    @staticmethod
    async def download_video(video_info: VideoDownloadSchema, format: str = "best[ext=mp4]") -> None:
        if Path(video_info.video_file_download_path).exists():
            logger.info(f"Видео уже скачано: {video_info.video_file_download_path}")
            return

        command = f'yt-dlp -f "{format}" -o "{video_info.video_file_download_path}" {video_info.video_url}'
        logger.debug("Downloading video: {}".format(video_info.video_url))
        logger.debug("Executing command: {}".format(command))
        process = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        _, stderr = await process.communicate()

        if process.returncode == 0:
            logger.info(f"Видео скачано: {video_info.video_file_download_path}")
        else:
            stderr_text = stderr.decode(locale.getpreferredencoding(False), errors="replace").strip()
            logger.error(f"Ошибка скачивания видео: {stderr_text}")

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
        logger.debug(f"video_ids_without_formats: {len(video_ids)}")
        for i, v_id in enumerate(video_ids):
            formats = self.get_video_formats(v_id)
            for format_data in formats:
                self._repository.add_video_format(format_data, v_id)
            logger.debug(f"[{i+1}/{len(video_ids)}] Added video formats for v_id: {v_id}")

    def get_video_formats(self, video_id: str) -> list[YTFormatSchema]:
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
            return []

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
            return []

    def channel_exist(self, channel_id: str) -> bool:
        return bool(self._repository.get_channel_by_id(channel_id))

    def video_exist(self, youtube_video_id: str) -> bool:
        return bool(self._repository.get_video(youtube_video_id))

    def _construct_video_path(self, video_id: str) -> Path:
        return Path(settings.video_download_path) / f"{video_id}.mp4"

    def _construct_thumbnail_path(self, video_id: str) -> Path:
        return Path(settings.thumbnail_download_path) / f"{video_id}.jpg"
