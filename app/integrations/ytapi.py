import os
import sys
from datetime import datetime

import googleapiclient.discovery
import httplib2
from googleapiclient.errors import HttpError
from loguru import logger
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

from app.config import settings
from app.db.base import Session
from app.db.data_table import Channel, Video
from app.db.repository import YoutubeDataRepository
from app.schema import ChannelAPIInfoSchema


class YTApiClient:
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
                    commentCount = int(item.get("statistics", {}).get("commentCount", 0))
                    tags = item.get("snippet", {}).get("tags", [])
                    defaultAudioLanguage = item.get("snippet", {}).get("defaultAudioLanguage", None)

                    # Проверка существования видео в базе данных
                    if not self._repository.get_video(video_id):
                        logger.warning(f"Video with ID {video_id} not found in the database. Skipping update.")
                        continue

                    self._repository.update_video_details(
                        video_id, upload_date, like_count, commentCount, tags, defaultAudioLanguage
                    )
                    logger.info(f"Updated video details for video ID {video_id}.")
                except Exception as e:
                    self._repository.set_video_as_invalid(video_id)
                    logger.error(f"Failed to update video details for video ID {video_id}. Error: {e}")

    def update_missing_video_info(self, videos_list: list[Video] = []):
        if not videos_list:
            videos_list = self._repository.get_videos_without_upload_date()
            logger.debug(f"videos_without_date: {len(videos_list)}")
        while videos_list:
            video_ids = [
                video.video_id for video in videos_list if video.like_count != -1
            ]  # Пропускаем видео с маркером неудачи

            # Предполагаем, что update_video_info обновляет данные успешно или устанавливает like_count = -1 при неудаче
            self.update_video_info(video_ids)

            # Fetch next batch of videos, уже с учетом маркера неудачи
            videos_list = self._repository.get_videos_without_upload_date()
        self._repository.reset_all_invalid_videos()

    def get_channel_info(self, channel_ids: list[str]) -> list[ChannelAPIInfoSchema]:
        # Disable OAuthlib's HTTPS verification when running locally.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        # Get credentials and create an API client
        flow = flow_from_clientsecrets(self.client_secrets_file, scope=self.scopes)
        storage = Storage("%s-oauth2.json" % sys.argv[0])
        credentials = storage.get()
        if credentials is None or credentials.invalid:
            flags = argparser.parse_args()
            credentials = run_flow(flow, storage, flags)

        youtube = googleapiclient.discovery.build(self.api_service_name, self.api_version, credentials=credentials)
        channels_info: list[ChannelAPIInfoSchema] = []

        try:
            request = youtube.channels().list(
                part="contentDetails,contentOwnerDetails,id,snippet,statistics,status,topicDetails",
                id=",".join(channel_ids),
            )
            response = request.execute()
            # Преобразуем ответ в объект ChannelAPIInfoSchema
            if "items" in response:
                for item in response["items"]:
                    channels_info.append(ChannelAPIInfoSchema.from_api_response(item))

            return channels_info
        except HttpError as e:
            logger.error(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
        except KeyError:
            logger.error("The response from the API did not contain the expected data.")
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}")
        return None

    def update_channels_info(self):
        channels_list: list[Channel] = self._repository.get_channels(limit=10)
        # logger.debug(channels_list)
        page = 1
        while channels_list:
            logger.debug(f"Updating info for {len(channels_list)} channels.")
            try:
                channel_ids = [ch.channel_id for ch in channels_list]
                channels = self.get_channel_info(channel_ids)
                for channel_api_info in channels:
                    self._repository.update_channel_details(channel_api_info)
            except Exception as e:
                logger.error("Failed to update channels info!")
                logger.error(e)
            # Загружаем следующую порцию каналов
            channels_list: list[Channel] = self._repository.get_channels(limit=10, page=page)
            page += 1
