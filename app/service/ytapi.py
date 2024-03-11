import os
import sys
from contextlib import suppress
from datetime import datetime

import googleapiclient.discovery
import googleapiclient.errors
import httplib2
from loguru import logger
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

from app.config import settings
from app.db.base import Session
from app.db.repository import YoutubeDataRepository


class YTApiService:
    def __init__(self):
        self.scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        self.api_service_name = "youtube"
        self.api_version = "v3"
        self.client_secrets_file = settings.youtube_secret_json
        self._repository = YoutubeDataRepository(session=Session())

    def get_video_info(self, video_id: list[str]) -> dict:
        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        # Get credentials and create an API client
        flow = flow_from_clientsecrets(self.client_secrets_file, scope=self.scopes)

        storage = Storage("%s-oauth2.json" % sys.argv[0])
        credentials = storage.get()
        if credentials is None or credentials.invalid:
            flags = argparser.parse_args()
            credentials = run_flow(flow, storage, flags)

        youtube = googleapiclient.discovery.build(
            self.api_service_name, self.api_version, http=credentials.authorize(httplib2.Http())
        )

        request = youtube.videos().list(part="snippet,statistics,status,contentDetails", id=",".join(video_id))
        response = request.execute()

        return response

    def update_video_info(self, video_ids: list[str]) -> None:
        video_info = self.get_video_info(video_ids)
        if "items" in video_info:
            for item in video_info["items"]:
                try:
                    video_id: str = item["id"]
                    upload_date = datetime.strptime(item["snippet"]["publishedAt"], "%Y-%m-%dT%H:%M:%SZ")
                    like_count = int(item.get("statistics", {}).get("likeCount", 0))
                    tags = item["snippet"].get("tags", [])

                    # Проверка существования видео в базе данных
                    if not self._repository.get_video(video_id):
                        logger.warning(f"Video with ID {video_id} not found in the database. Skipping update.")
                        continue

                    self._repository.update_video_details(video_id, upload_date, like_count, tags)
                    logger.info(f"Updated video details for video ID {video_id}.")
                except Exception as e:
                    self._repository.set_video_as_invalid(video_id)
                    logger.error(f"Failed to update video details for video ID {video_id}. Error: {e}")

    def update_missing_video_info(self):
        videos_without_date = self._repository.get_videos_without_upload_date()
        logger.debug(len(videos_without_date))
        while videos_without_date:
            video_ids = [
                video.video_id for video in videos_without_date if video.like_count != -1
            ]  # Пропускаем видео с маркером неудачи

            # Предполагаем, что update_video_info обновляет данные успешно или устанавливает like_count = -1 при неудаче
            self.update_video_info(video_ids)

            # Fetch next batch of videos, уже с учетом маркера неудачи
            videos_without_date = self._repository.get_videos_without_upload_date()
        self._repository.reset_all_invalid_videos()
