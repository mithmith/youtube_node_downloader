import asyncio
import glob
import json
import locale
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

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
    async def download_video(
        video_info: VideoDownloadSchema,
        format: str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        ensure_mp4: bool = True,
    ) -> None:
        out_path = Path(video_info.video_file_download_path)
        if out_path.exists():
            logger.info(f"Видео уже скачано: {out_path}")
            return

        postproc_flag = "--recode-video mp4" if ensure_mp4 else "--merge-output-format mp4"
        command = f'yt-dlp -f "{format}" {postproc_flag} -o "{out_path}" {video_info.video_url}'

        logger.debug(f"Downloading video: {video_info.video_url}")
        logger.debug(f"Command: {command}")

        proc = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()

        if proc.returncode == 0:
            logger.info(f"Видео скачано: {out_path}")
        else:
            err = stderr.decode(locale.getpreferredencoding(False), "replace").strip()
            logger.error(f"Ошибка скачивания видео: {err}")

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

    @staticmethod
    def get_video_formats(video_id: str) -> list[YTFormatSchema]:
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

    @staticmethod
    def fetch_transcript(
        video_id: str,
        preferred_langs: tuple[str, ...] = ("ru",),
    ) -> Optional[str]:
        """
        Возвращает расшифровку речи YouTube-видео (чистый текст без тайм-кодов).

        Порядок поиска языка:
        1. Перебор preferred_langs в automatic_captions
        2. Первый язык из automatic_captions
        3. Перебор preferred_langs в subtitles
        4. Первый язык из subtitles
        5. None, если субтитров нет

        Parameters
        ----------
        video_id : str
            Идентификатор ролика (например, '7NSBuTHngK0').
        preferred_langs : tuple[str, ...], optional
            Коды языков, которые пробуем в первую очередь.

        Returns
        -------
        str | None
            Сплошной текст субтитров или None, если ничего не найдено.
        """
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # 1. Получаем метаданные ролика
        try:
            proc = subprocess.run(
                ["yt-dlp", "-j", video_url],
                check=True,
                capture_output=True,
                text=True,
            )
            info = json.loads(proc.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            logger.error(f"Не удалось получить JSON-метаданные: {e}")
            return None

        auto_caps: dict[str, list] = info.get("automatic_captions", {}) or {}
        man_caps: dict[str, list] = info.get("subtitles", {}) or {}

        # 2. Выбираем язык и тип субтитров
        lang, use_auto = None, None

        for pl in preferred_langs:
            if pl in auto_caps:
                lang, use_auto = pl, True
                break
        if lang is None and auto_caps:
            lang, use_auto = next(iter(auto_caps)), True

        if lang is None:
            for pl in preferred_langs:
                if pl in man_caps:
                    lang, use_auto = pl, False
                    break
        if lang is None and man_caps:
            lang, use_auto = next(iter(man_caps)), False

        if lang is None:
            logger.warning(f"У ролика {video_id} нет субтитров")
            return None

        # 3. Скачиваем json3 и читаем
        with tempfile.TemporaryDirectory() as tmpdir:
            outtmpl = os.path.join(tmpdir, "subs")  # yt-dlp → subs.<lang>.json3
            cmd = [
                "yt-dlp",
                "--skip-download",
                "--sub-lang",
                lang,
                "--sub-format",
                "json3",
                "-o",
                outtmpl,
                video_url,
            ]
            cmd.insert(1, "--write-auto-subs" if use_auto else "--write-subs")

            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"Ошибка скачивания субтитров: {e.stderr.strip()}")
                return None

            pattern = os.path.join(tmpdir, f"subs.{lang}*.json3")
            files = glob.glob(pattern)
            if not files:
                logger.error(f"Файл субтитров не найден ({pattern})")
                return None

            try:
                with open(files[0], encoding="utf-8") as fp:
                    data = json.load(fp)
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"Не удалось прочитать JSON3 файл: {e}")
                return None

        # 4. Превращаем JSON3 в сплошной текст
        if "events" not in data:
            logger.error("JSON3 не содержит ключ 'events'")
            return None

        text_chunks = [seg["utf8"] for ev in data["events"] if "segs" in ev for seg in ev["segs"] if "utf8" in seg]
        # Убираем лишние пробелы/переводы строк подряд
        transcript = re.sub(r"\s+", " ", " ".join(text_chunks)).strip()

        logger.info(f"Расшифровка {video_id} ({lang}) успешно получена ({len(transcript)} символов)")
        return transcript

    def channel_exist(self, channel_id: str) -> bool:
        return bool(self._repository.get_channel_by_id(channel_id))

    def video_exist(self, youtube_video_id: str) -> bool:
        return bool(self._repository.get_video(youtube_video_id))

    def _construct_video_path(self, video_id: str) -> Path:
        return Path(settings.video_download_path) / f"{video_id}.mp4"

    def _construct_thumbnail_path(self, video_id: str) -> Path:
        return Path(settings.thumbnail_download_path) / f"{video_id}.jpg"
