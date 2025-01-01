import os
import pickle
from datetime import datetime

import googleapiclient.discovery
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.errors import HttpError
from loguru import logger

from app.config import settings
from app.db.base import Session
from app.db.data_table import Channel, Video
from app.db.repository import YoutubeDataRepository
from app.schema import ChannelAPIInfoSchema


class YTApiClient:
    def __init__(self):
        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        self.scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        self.api_service_name = "youtube"
        self.api_version = "v3"
        self._client_secrets_file = settings.youtube_secret_json
        self._repository = YoutubeDataRepository(session=Session())
        self._credentials_file = f"google-oauth2.pickle"

    def _get_credentials(self):
        """Получить или обновить учетные данные."""
        credentials = None

        # Load credentials from file if available
        if os.path.exists(self._credentials_file):
            with open(self._credentials_file, "rb") as token:
                credentials = pickle.load(token)

        # Check if credentials are valid
        if not credentials or not credentials.valid:
            try:
                if credentials and credentials.expired and credentials.refresh_token:
                    # Refresh existing credentials
                    credentials.refresh(Request())
                else:
                    # Perform full authorization
                    flow = InstalledAppFlow.from_client_secrets_file(self._client_secrets_file, self.scopes)
                    credentials = flow.run_local_server(port=0)

                # Save credentials for future use
                with open(self._credentials_file, "wb") as token:
                    pickle.dump(credentials, token)
            except RefreshError:
                logger.error("Refresh token invalid or expired. Removing old credentials.")
                if os.path.exists(self._credentials_file):
                    os.remove(self._credentials_file)
                flow = InstalledAppFlow.from_client_secrets_file(self._client_secrets_file, self.scopes)
                credentials = flow.run_local_server(port=0)
                with open(self._credentials_file, "wb") as token:
                    pickle.dump(credentials, token)

        return credentials
    
    def _make_request(self, func, *args, **kwargs):
        """Выполнить запрос к YouTube API с повторной попыткой в случае ошибки."""
        try:
            return func(*args, **kwargs)
        except HttpError as e:
            if e.resp.status in [401, 403]:
                os.remove(self._credentials_file)  # Удаляем просроченные учетные данные
                credentials = self._get_credentials()  # Получаем новые учетные данные
                youtube = googleapiclient.discovery.build(
                    self.api_service_name, self.api_version, credentials=credentials
                )
                return func(*args, **kwargs)  # Повторяем запрос с новыми учетными данными
            else:
                raise

    def get_video_info(self, video_ids: list[str]) -> list[dict]:
        """
        Retrieve detailed information for a list of videos using the YouTube API.

        Args:
            video_ids (list[str]): List of video IDs.

        Returns:
            list[dict]: A list of video details retrieved from the YouTube API.
        """
        youtube = googleapiclient.discovery.build(
            self.api_service_name, self.api_version, credentials=self._get_credentials()
        )
        
        # Split the video IDs into chunks of 50
        chunk_size = 50
        video_chunks = [video_ids[i:i + chunk_size] for i in range(0, len(video_ids), chunk_size)]
        all_videos_info = []

        for chunk in video_chunks:
            try:
                request_func = (
                    lambda: youtube.videos()
                    .list(
                        part="snippet,statistics,status,contentDetails",
                        id=",".join(chunk),
                    )
                    .execute()
                )
                response = self._make_request(request_func)
                all_videos_info.extend(response.get("items", []))  # Add video data to the results
            except Exception as e:
                logger.error(f"Error retrieving video info for chunk {chunk}: {e}")
        return all_videos_info


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
        credentials = self._get_credentials()
        youtube = googleapiclient.discovery.build(self.api_service_name, self.api_version, credentials=credentials)
        channels_info: list[ChannelAPIInfoSchema] = []

        request_func = (
            lambda: youtube.channels()
            .list(
                part="contentDetails,contentOwnerDetails,id,snippet,statistics,status,topicDetails",
                id=",".join(channel_ids),
            )
            .execute()
        )
        response = self._make_request(request_func)

        try:
            # Преобразуем ответ в объект ChannelAPIInfoSchema
            if "items" in response:
                for item in response["items"]:
                    channels_info.append(ChannelAPIInfoSchema.from_api_response(item))

            return channels_info
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
