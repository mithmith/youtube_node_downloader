from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError

from app.db.base import BaseRepository
from app.db.data_table import Channel, Tag, Thumbnail, Video, VideoTag, YTFormat
from app.schema import ChannelAPIInfoSchema, ChannelInfoSchema, ThumbnailSchema, VideoSchema, YTFormatSchema


class YoutubeDataRepository(BaseRepository[Channel]):
    model = Channel

    def add_video_metadata(self, video_entry: VideoSchema, channel_id: str) -> None:
        # Добавляем видео с использованием обновленной функции add_video
        self.add_video(video_entry, channel_id, video_entry.tags, video_entry.thumbnails)
        logger.info(f"Video '{video_entry.title}' metadata added successfully.")

    def add_video(
        self,
        video_schema: VideoSchema,  # Используем схему Pydantic напрямую
        channel_id: str,
        tags: list[str],
        thumbnails_schemas: list[ThumbnailSchema],  # Используем список схем
    ) -> Video:
        # Проверяем, существует ли канал
        channel: Channel = self._session.get(Channel, channel_id)
        if not channel:
            logger.error(f"Channel with ID {channel_id} not found.")
            raise ValueError("Channel not found")

        with self._session.no_autoflush:
            # Создание или обновление объекта Video
            video: Video = self._session.query(Video).filter_by(video_id=video_schema.id).first()
            if not video:
                video = Video(video_id=video_schema.id, channel_id=channel_id)
                self._session.add(video)

            upload_date = datetime.utcfromtimestamp(video_schema.timestamp) if video_schema.timestamp else None
            video.title = video_schema.title
            video.description = video_schema.description
            video.url = video_schema.url
            video.duration = video_schema.duration or 0
            video.view_count = video_schema.view_count
            video.upload_date = upload_date
            # Сохраняем видео в базе данных, чтобы получить video.id
            self.commit()

            # Используем функцию bulk_add_tags для добавления тегов
            self.bulk_add_tags(tags)

            # Для каждого тега создаем связь между видео и тегом
            for tag_name in tags:
                tag: Tag = self._session.query(Tag).filter_by(name=tag_name).first()
                # Проверка существования связи между видео и тегом
                existing_video_tag = self._session.query(VideoTag).filter_by(video_id=video.id, tag_id=tag.id).first()
                if existing_video_tag is None:
                    video_tag = VideoTag(video_id=video.id, tag_id=tag.id)
                    self._session.add(video_tag)
            self.commit()

            # Используем функцию add_thumbnail для добавления миниатюр
            for thumbnail_schema in thumbnails_schemas:
                self.add_thumbnail(thumbnail_schema, video.id)
        self.commit()
        return video

    def add_tag(self, tag_name: str) -> Tag:
        try:
            tag: Tag = self._session.query(Tag).filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                self._session.add(tag)
                self.commit()
            return tag
        except Exception as e:
            logger.error(f"Error adding tag: {e}")
            self._session.rollback()
            raise

    def add_thumbnail(
        self, thumbnail_data: ThumbnailSchema, video_id: UUID = None, channel_id: str = None
    ) -> Thumbnail:
        try:
            if video_id:
                # Проверяем наличие видео по его ID
                video: Video = self._session.get(Video, video_id)
                if not video:
                    logger.error(f"Video with ID {video_id} not found.")
                    raise ValueError("Video not found")
            if channel_id:
                # Проверяем наличие видео по его ID
                channel: Channel = self._session.get(Channel, channel_id)
                if not channel:
                    logger.error(f"Channel with ID {channel_id} not found.")
                    raise ValueError("Channel not found")

            # Пытаемся найти существующую миниатюру с такими же url, width и height
            existing_thumbnail = self._session.query(Thumbnail).filter_by(url=thumbnail_data.url).first()
            if existing_thumbnail:
                return existing_thumbnail

            thumbnail = Thumbnail(
                **thumbnail_data.model_dump(exclude_unset=True, exclude={"id"}),
                video_id=video.id if video_id else None,
                channel_id=channel.channel_id if channel_id else None,
                id=uuid4(),
                thumbnail_id=thumbnail_data.id,
            )
            self._session.add(thumbnail)
            self._session.commit()
            return thumbnail
        except Exception as e:
            logger.error(f"Error adding thumbnail: {e}")
            self._session.rollback()
            raise

    def get_channel_id_by_url(self, channel_url: str) -> str | None:
        channel: Channel = self._session.query(Channel).filter_by(channel_url=channel_url).first()
        if channel:
            return channel.channel_id
        else:
            logger.warning(f"Channel with URL {channel_url} not found.")
            return None

    def get_channel_videos(self, channel_id: str) -> list[Video]:
        try:
            return self._session.query(Video).filter_by(channel_id=channel_id).all()
        except NoResultFound:
            logger.warning(f"No videos found for channel ID {channel_id}")
            return []

    def add_or_update_channel(self, channel_data: ChannelInfoSchema) -> Channel:
        channel_id = channel_data.channel_id
        channel: Channel = self._session.query(Channel).filter_by(channel_id=channel_id).first()

        channel_dict = channel_data.model_dump(
            exclude_unset=True,
            exclude={
                "entries",
                "availability",
                "thumbnails",
                "uploader_id",
                "uploader_url",
            },
        )

        if channel:
            # Обновляем существующий объект Channel
            for key, value in channel_dict.items():
                if hasattr(channel, key):
                    setattr(channel, key, value)
        else:
            # Создаём новый объект Channel и добавляем его в сессию
            channel = Channel(**channel_dict)
            self._session.add(channel)
        self.commit()
        for thumbnail_schema in channel_data.thumbnails:
            self.add_thumbnail(thumbnail_schema, channel_id=channel_data.channel_id)
        self.commit()
        return channel

    def get_channels(self, limit: int = 50, page: int = 0):
        try:
            return (
                self.session.query(Channel).order_by(Channel.published_at.asc()).limit(limit).offset(page * limit).all()
            )
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении каналов: {e}")
            return []

    def update_channel_details(self, channel_info: ChannelAPIInfoSchema):
        channel: Channel = self._session.query(Channel).filter_by(channel_id=channel_info.id).first()
        channel_dict = channel_info.model_dump(
            exclude_unset=True
        )  # Получаем словарь значений, исключая неустановленные

        if channel:
            # Обновляем существующий объект Channel, если он найден
            for key, value in channel_dict.items():
                if hasattr(channel, key):
                    setattr(channel, key, value)  # Обновляем атрибут, если он существует
        else:
            # Если канал не найден, создаем новый с использованием значений из channel_info
            new_channel_data = {key: value for key, value in channel_dict.items() if hasattr(Channel, key)}
            new_channel = Channel(**new_channel_data)
            self._session.add(new_channel)
        self.commit()

    def get_videos_without_upload_date(self, limit: int = 30) -> list[Video]:
        return (
            self.session.query(Video)
            .filter(Video.upload_date.is_(None))
            .filter(or_(Video.like_count.is_(None), Video.like_count != -1))
            .limit(limit)
            .all()
        )

    def get_video_ids_without_formats(self, limit: int = 50) -> list[str]:
        # Создаем подзапрос для получения уникальных video_id из таблицы video_formats
        subquery = self.session.query(YTFormat.video_id).distinct().subquery()

        # Формируем основной запрос, используя LEFT OUTER JOIN и фильтруя результаты так, чтобы в ответе остались только те видео,
        # для которых нет записей в подзапросе
        query = (
            self.session.query(Video.video_id)
            .outerjoin(subquery, Video.id == subquery.c.video_id)
            .filter(subquery.c.video_id == None)
            .limit(limit)
        )

        # Выполняем запрос и возвращаем результаты
        video_ids = query.all()

        # Преобразуем результат в список строк
        return [video_id[0] for video_id in video_ids]

    def get_video(self, youtube_video_id: str) -> Video | None:
        video: Video = self.session.query(Video).filter_by(video_id=youtube_video_id).first()
        if video:
            return video
        logger.warning(f"Video with youtube video_id '{youtube_video_id}' not found.")
        return None

    def update_video_details(
        self,
        video_id: str,
        upload_date: datetime,
        like_count: int,
        commentCount: int,
        tags: list[str],
        defAudioLang: str,
    ) -> None:
        video: Video = self._session.query(Video).filter_by(video_id=video_id).first()
        if video:
            video.upload_date = upload_date
            video.like_count = like_count
            self.commit()
            self.bulk_add_tags(tags)

            # Получаем все существующие ID тегов
            existing_tag_ids = {tag.id for tag in self._session.query(Tag).filter(Tag.name.in_(tags)).all()}

            # Удаляем все предыдущие связи между видео и тегами
            self._session.query(VideoTag).filter(VideoTag.video_id == video.id).delete(synchronize_session="fetch")

            # Добавляем новые связи между видео и тегами
            for tag_id in existing_tag_ids:
                video_tag = VideoTag(video_id=video.id, tag_id=tag_id)
                self._session.add(video_tag)

            self.commit()
        else:
            logger.error(f"Video with ID {video_id} not found in the database.")

    def set_video_as_invalid(self, video_id: str):
        video: Video = self._session.query(Video).filter_by(video_id=video_id).first()
        if video:
            video.like_count = -1
            self.commit()
        else:
            logger.error(f"Video with ID {video_id} not found in the database.")

    def reset_all_invalid_videos(self):
        videos: list[Video] = self._session.query(Video).filter(Video.like_count == -1).all()
        for video in videos:
            video.like_count = 0  # Сбросить маркер неудачи на нейтральное/начальное значение
        self._session.commit()
        logger.info(f"Reset invalid markers for {len(videos)} videos.")

    def delete_video(self, video_id: UUID):
        video: Video = self._session.get(Video, str(video_id))
        if video:
            self._session.delete(video)
            self.commit()
        else:
            logger.warning(f"Video with ID {video_id} not found.")

    def add_video_format(self, format_data: YTFormatSchema, youtube_video_id: str) -> YTFormat:
        # Сначала находим видео по его youtube_video_id
        video: Video = self._session.query(Video).filter_by(video_id=youtube_video_id).first()
        if not video:
            logger.error(f"Video with youtube_video_id '{youtube_video_id}' not found.")
            return None

        # Преобразовываем format_data в словарь для удобства
        format_dict = format_data.model_dump(exclude_unset=True)
        # Проверяем, существует ли уже формат с таким format_id для данного видео
        yt_format: YTFormat = (
            self._session.query(YTFormat).filter_by(video_id=video.id, format_id=format_dict["format_id"]).first()
        )

        if yt_format:
            # Обновляем существующий формат
            for key, value in format_dict.items():
                setattr(yt_format, key, value)
        else:
            # Создаём новый объект YTFormat и добавляем его в сессию
            format_dict["video_id"] = video.id  # Присваиваем ID видео
            new_format = YTFormat(**format_dict)
            self._session.add(new_format)

        self.commit()
        return yt_format if yt_format else new_format

    def bulk_add_tags(self, tags: list[str]) -> None:
        existing_tags: list[Tag] = self._session.query(Tag).filter(Tag.name.in_(tags)).all()
        existing_tag_names = {tag.name for tag in existing_tags}

        # Убедимся, что новые теги уникальны перед добавлением
        unique_new_tags = set(tags) - existing_tag_names
        new_tags = [Tag(name=tag_name) for tag_name in unique_new_tags]

        if new_tags:
            try:
                self._session.bulk_save_objects(new_tags)
                self.commit()
            except IntegrityError as e:
                self._session.rollback()  # Откатываем транзакцию в случае ошибки
                logger.error(f"Error during bulk add tags: {e}")

    def update_video_path(self, video_id: UUID, video_path: Path) -> None:
        video: Video = self._session.query(Video).filter_by(id=video_id).first()
        if video:
            video.video_path = str(video_path)
            self._session.commit()
        else:
            logger.warning(f"Video with ID {video_id} not found.")

    def update_thumbnail_path(self, video_id: UUID, thumbnail_url: str, thumbnail_path: Path) -> None:
        # Находим конкретную миниатюру по video_id и thumbnail_url
        thumbnail: Thumbnail = self._session.query(Thumbnail).filter_by(video_id=video_id, url=thumbnail_url).first()
        if thumbnail:
            # Обновляем путь к файлу миниатюры
            thumbnail.thumbnail_path = str(thumbnail_path)
            self._session.commit()
        else:
            logger.warning(f"Thumbnail not found for video ID {video_id} with URL {thumbnail_url}.")
