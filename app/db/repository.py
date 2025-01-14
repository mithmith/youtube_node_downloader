from datetime import datetime
from pathlib import Path
from typing import Union, Optional
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError

from app.db.base import BaseRepository
from app.db.data_table import Channel, ChannelHistory, Tag, Thumbnail, Video, VideoHistory, VideoTag, YTFormat
from app.schema import ChannelAPIInfoSchema, ChannelInfoSchema, ThumbnailSchema, VideoSchema, YTFormatSchema


class YoutubeDataRepository(BaseRepository[Channel]):
    model = Channel

    def add_channel(self, channel_data: ChannelInfoSchema) -> Channel:
        """
        Adds a new channel or updates an existing one in the database based on the provided channel data.

        Args:
            channel_data (ChannelInfoSchema): A schema instance containing all necessary channel data.

        Returns:
            Channel: The newly added or updated channel entity.

        Raises:
            SQLAlchemyError: If there is a database operation error.

        Description:
            This method checks if a channel exists in the database based on the `channel_id` provided within
            the `channel_data`. If the channel exists, it updates its fields with the new data. If it does not exist,
            a new channel instance is created and added to the database. It commits the session after adding or
            updating the channel. Thumbnails associated with the channel are also added by invoking the `add_thumbnail` method.
        """
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
        with self._session.no_autoflush:
            if channel:
                # Update the existing Channel object
                for key, value in channel_dict.items():
                    if hasattr(channel, key):
                        setattr(channel, key, value)
            else:
                # Create a new Channel object and add it to the session
                channel = Channel(**channel_dict)
                self._session.add(channel)
            self.commit()
            for thumbnail_schema in channel_data.thumbnails:
                self.add_thumbnail(thumbnail_schema, channel_id=channel_data.channel_id)
        self.commit()
        return channel

    def add_video(self, video_schema: VideoSchema, channel_id: str) -> Video:
        """
        Adds a new video or updates an existing one based on the provided video schema.

        Args:
            video_schema (VideoSchema): The schema containing video data.
            channel_id (str): The ID of the channel to which the video belongs.

        Returns:
            Video: The newly added or updated video object.

        Raises:
            ValueError: If the channel associated with the video does not exist in the database.
            SQLAlchemyError: If there is a database operation error.

        Description:
            This method first checks if the channel exists in the database. If not, it raises a ValueError.
            If the channel exists, it checks if the video already exists. If it does not, it creates a new video object and
            adds it to the session. It then updates the video's attributes with data from the video schema and commits the session.
            The method also manages tags and thumbnails by adding new ones or linking existing ones to the video.
        """
        # Check if the channel exists
        if not self._session.get(Channel, channel_id):
            logger.error(f"Channel with ID {channel_id} not found.")
            raise ValueError("Channel not found")

        with self._session.no_autoflush:
            # Create or update the Video object
            video: Video = self._session.query(Video).filter_by(video_id=video_schema.id).first()
            if not video:
                video = Video.from_schema(video_schema, channel_id)
                self._session.add(video)

            # Save the video to obtain video.id
            self.commit()

            # Manage tags using bulk_add_tags
            self.bulk_add_tags(video_schema.tags)

            # Create link between video and tags
            for tag_name in video_schema.tags:
                tag: Tag = self._session.query(Tag).filter_by(name=tag_name).first()
                existing_video_tag = self._session.query(VideoTag).filter_by(video_id=video.id, tag_id=tag.id).first()
                if existing_video_tag is None:
                    video_tag = VideoTag(video_id=video.id, tag_id=tag.id)
                    self._session.add(video_tag)
            self.commit()

            # Add thumbnails
            for thumbnail_schema in video_schema.thumbnails:
                self.add_thumbnail(thumbnail_schema, video.id)

        self.commit()
        logger.info(f"Video '{video_schema.title}' metadata added successfully.")
        return video

    def add_tag(self, tag_name: str) -> Tag:
        """
        Adds a new tag to the database or returns the existing one.

        Args:
            tag_name (str): The name of the tag to add or find.

        Returns:
            Tag: The Tag object either retrieved or created.

        Raises:
            Exception: Raises an exception if there's a problem adding the tag to the database, including integrity errors.

        Description:
            This method checks if the tag with the specified name exists in the database. If the tag does not exist, it creates
            a new Tag object, adds it to the session, and commits the session to save changes. If an error occurs during the
            database operation, it logs the error, rolls back the transaction, and re-raises the exception to ensure that
            database integrity is maintained and the error is not silently ignored.
        """
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
        """
        Adds a thumbnail to the database or returns the existing one based on the URL.

        Args:
            thumbnail_data (ThumbnailSchema): Data schema for the thumbnail.
            video_id (UUID, optional): UUID of the video the thumbnail is associated with.
            channel_id (str, optional): ID of the channel the thumbnail is associated with.

        Returns:
            Thumbnail: The Thumbnail object either retrieved or created.

        Raises:
            ValueError: If the provided video_id or channel_id does not correspond to any existing record.
            Exception: If there is a problem with adding the thumbnail to the database.

        Description:
            This method first checks if there's an existing video or channel with the provided IDs. It then checks if
            a thumbnail with the same URL already exists. If it does, it returns that existing thumbnail. Otherwise,
            it creates a new Thumbnail object using the data provided, adds it to the session, and commits the session
            to save the changes. If any exception occurs during these operations, the transaction is rolled back and the
            exception is logged and re-raised.
        """
        try:
            if video_id:
                video: Video = self._session.get(Video, video_id)
                if not video:
                    logger.error(f"Video with ID {video_id} not found.")
                    raise ValueError("Video not found")
            if channel_id:
                channel: Channel = self._session.get(Channel, channel_id)
                if not channel:
                    logger.error(f"Channel with ID {channel_id} not found.")
                    raise ValueError("Channel not found")

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

    def add_video_format(self, format_data: YTFormatSchema, youtube_video_id: str) -> YTFormat:
        """
        Adds or updates a video format in the database based on the provided format data.

        Args:
            format_data (YTFormatSchema): Data schema for the video format.
            youtube_video_id (str): YouTube video ID for which the format is being added or updated.

        Returns:
            YTFormat: The newly created or updated YTFormat object.

        Raises:
            ValueError: If the video associated with youtube_video_id does not exist.

        Description:
            This method retrieves a video by its YouTube video ID. If the video is found, it then checks if a format with
            the specified format ID already exists for that video. If it exists, the existing format is updated with the new
            data. If it does not exist, a new YTFormat object is created and added to the session. The changes are then
            committed to the database. If the video is not found, an error is logged, and None is returned.
        """
        video: Video = self._session.query(Video).filter_by(video_id=youtube_video_id).first()
        if not video:
            logger.error(f"Video with youtube_video_id '{youtube_video_id}' not found.")
            raise ValueError("Video not found")

        format_dict = format_data.model_dump(exclude_unset=True)
        yt_format: YTFormat = (
            self._session.query(YTFormat).filter_by(video_id=video.id, format_id=format_dict["format_id"]).first()
        )

        if yt_format:
            # Update existing format
            for key, value in format_dict.items():
                setattr(yt_format, key, value)
        else:
            # Create new format object and add to session
            format_dict["video_id"] = video.id
            new_format = YTFormat(**format_dict)
            self._session.add(new_format)

        self.commit()
        return yt_format if yt_format else new_format

    def add_channel_history(self, channel_info: Channel | ChannelHistory) -> None:
        """
        Adds historical data for a channel to the database.

        Args:
            channel_info (Channel): The channel object containing the data to record in history.

        Returns:
            None

        Description:
            This method creates a new ChannelHistory record using the data from the provided Channel object.
            The historical data includes the channel's follower count, view count, and video count at the time of this call.
            The method logs the action and commits the new ChannelHistory record to the database.
        """
        if isinstance(channel_info, ChannelHistory):
            history = channel_info
        else:
            history: ChannelHistory = ChannelHistory(
                channel_id=channel_info.channel_id,
                follower_count=channel_info.channel_follower_count,
                view_count=channel_info.viewCount,
                video_count=channel_info.videoCount,
            )
        self.add(history)

    def add_video_history(self, video_schema: VideoSchema) -> None:
        """Adds historical data for a video to the database."""
        video: Video = self.get_video_by_id(youtube_video_id=video_schema.id)
        video_history: VideoHistory = VideoHistory(
            video_id=video.id,
            view_count=video_schema.view_count,
            like_count=video_schema.like_count,
            comment_count=video_schema.commentCount,
        )
        self.add(video_history)

    def get_channel_by_id(self, channel_id: str) -> Optional[Channel]:
        channel: Channel = self.session.query(Channel).filter_by(channel_id=channel_id).first()
        if channel:
            return channel
        logger.warning(f"Channel with youtube channel_id '{channel_id}' not found.")
        return None

    def get_video_by_id(self, youtube_video_id: str) -> Optional[Video]:
        """
        Retrieves a video from the database using its YouTube video ID.

        Args:
            youtube_video_id (str): The YouTube ID of the video to retrieve.

        Returns:
            Video | None: The retrieved video object if found, otherwise None.

        Description:
            This method searches the database for a video that matches the given YouTube video ID.
            If found, it returns the Video object; otherwise, it logs a warning and returns None.
            This function is essential for operations that need to verify the existence of a video
            before performing further actions or updates based on that video.
        """
        video: Video = self.session.query(Video).filter_by(video_id=youtube_video_id).first()
        if video:
            return video
        logger.warning(f"Video with youtube video_id '{youtube_video_id}' not found.")
        return None

    def get_channels(self, limit: int = 50, page: int = 0) -> list[Channel]:
        """
        Retrieves a paginated list of channels from the database.

        Args:
            limit (int): The maximum number of channels to return.
            page (int): The page number to retrieve, based on the limit.

        Returns:
            List[Channel]: A list of Channel objects. The list can be empty if no channels are found.

        Description:
            This method fetches a paginated list of channels sorted by their published date in ascending order.
            It utilizes SQL OFFSET for pagination, calculated as `page * limit`. This allows fetching subsets of
            channels for large datasets, reducing memory overhead and improving response times. If an error occurs
            during the query, it logs the error and returns an empty list to ensure the calling function can handle
            the result gracefully.
        """
        try:
            return (
                self.session.query(Channel).order_by(Channel.published_at.asc()).limit(limit).offset(page * limit).all()
            )
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving channels: {e}")
            return []

    def get_channel_videos(self, channel_id: str) -> list[Video]:
        """
        Retrieves all videos associated with a specific channel ID from the database.

        Args:
            channel_id (str): The unique identifier for the channel.

        Returns:
            List[Video]: A list of Video objects associated with the given channel ID.
                        The list can be empty if no videos are found for the specified channel.

        Description:
            This method fetches all videos linked to a specific channel ID. It queries the Video table
            filtering by 'channel_id'. If no videos are found matching the criteria, it returns an empty list
            and logs a warning. This method ensures that any consumer of the function can handle the output
            without having to deal with exceptions directly from the query.
        """
        try:
            return self._session.query(Video).filter_by(channel_id=channel_id).all()
        except NoResultFound:
            logger.warning(f"No videos found for channel ID {channel_id}")
            return []

    def get_channel_id_by_url(self, channel_url: str) -> Optional[str]:
        """
        Retrieves the channel ID based on a given channel URL from the database.

        Args:
            channel_url (str): The URL of the channel.

        Returns:
            str | None: The channel ID if found, otherwise None.

        Description:
            This method attempts to find a channel by its URL in the database. If found, it returns the channel's
            ID; otherwise, it logs a warning and returns None. This function allows for easy retrieval of channel
            IDs without exposing the underlying database query details, providing a clean interface for users who
            need to get channel IDs based on URLs.
        """
        channel: Channel = self._session.query(Channel).filter_by(channel_url=channel_url).first()
        if channel:
            return channel.channel_id
        else:
            logger.warning(f"Channel with URL {channel_url} not found.")
            return None

    def get_videos_without_upload_date(self, limit: int = 30) -> list[Video]:
        """
        Retrieves a list of videos that do not have an upload date set, up to a specified limit.

        Args:
            limit (int): The maximum number of videos to retrieve.

        Returns:
            list[Video]: A list of videos without an upload date.

        Description:
            This method queries the database to find videos where the upload date is not set. It provides an
            additional filter to include videos where the like count is either not set or not equal to -1,
            typically used to denote an error or placeholder value. This method is useful for identifying
            videos that might have incomplete data, allowing for further updates or corrections.
        """
        return (
            self.session.query(Video)
            .filter(Video.upload_date.is_(None))
            .filter(or_(Video.like_count.is_(None), Video.like_count != -1))
            .limit(limit)
            .all()
        )

    def get_video_ids_without_formats(self, limit: int = 50) -> list[str]:
        """
        Retrieves a list of video IDs that do not have any associated format entries, up to a specified limit.
        """
        # Creating a subquery to get distinct video IDs from the video_formats table
        subquery = self.session.query(YTFormat.video_id).distinct().subquery()

        # Main query using LEFT OUTER JOIN and filtering to ensure we return only videos without format entries
        query = (
            self.session.query(Video.video_id)
            .outerjoin(subquery, Video.id == subquery.c.video_id)
            .filter(subquery.c.video_id == None)
            .limit(limit)
            .offset(0)
        )

        # Executing the query and returning the results
        video_ids = query.all()

        # Converting the results to a list of strings
        return [video_id[0] for video_id in video_ids]

    def get_new_and_existing_video_ids(self, video_ids: list[str], channel_id: str) -> tuple[list[str], list[str]]:
        """
        Determines which video IDs from a given list are new and which already exist in the database for a specific channel.

        Args:
            video_ids (list[str]): A list of video IDs to check.
            channel_id (str): The ID of the channel to check against.

        Returns:
            tuple[list[str], list[str]]: A tuple containing two lists:
                - The first list contains new video IDs that do not exist in the database.
                - The second list contains existing video IDs that are already in the database.

        Description:
            This method checks a list of video IDs against the 'videos' table in the database to determine which videos are
            new and which are already associated with a specific channel. This helps in filtering out videos that need
            to be added to the database and those that do not require action. The method uses a simple query to fetch
            existing video IDs for the specified channel and then compares them with the provided list of video IDs.
        """
        existing_v_ids = set(
            v_id[0] for v_id in self.session.query(Video.video_id).filter(Video.channel_id == channel_id).all()
        )
        new_v_ids = [v_id for v_id in video_ids if v_id not in existing_v_ids]
        return new_v_ids, existing_v_ids

    def upsert_channel(self, channel_data: Union[ChannelInfoSchema, ChannelAPIInfoSchema]) -> Channel:
        """
        Updates the details of an existing channel or creates a new channel if it does not exist.

        Args:
            channel_data (Union[ChannelInfoSchema, ChannelAPIInfoSchema]): Schema containing channel information.

        Returns:
            Channel: The updated or newly created channel entity.

        Description:
            This method updates an existing channel in the database or creates a new channel if it does not exist.
            It uses the provided schema to populate the fields of the channel entity.
            The `last_update` field is automatically set to the current timestamp.
        """
        try:
            # Extract channel_id and check if the channel exists
            channel_id = getattr(channel_data, "channel_id", None) or getattr(channel_data, "id", None)
            if not channel_id:
                raise ValueError("Channel data must contain 'channel_id' or 'id' field.")

            channel: Channel = self._session.query(Channel).filter_by(channel_id=channel_id).first()

            # Convert schema data to dictionary, excluding unset or irrelevant fields
            channel_dict = channel_data.model_dump(exclude_unset=True)

            if channel:
                # Update existing channel
                for key, value in channel_dict.items():
                    if hasattr(channel, key):
                        setattr(channel, key, value)
                channel.last_update = datetime.now().replace(microsecond=0)
            else:
                # Create a new channel
                new_channel_data = {key: value for key, value in channel_dict.items() if hasattr(Channel, key)}
                new_channel_data["last_update"] = datetime.now().replace(microsecond=0)
                channel = Channel(**new_channel_data)
                self._session.add(channel)

            # Commit the transaction
            self.commit()
            logger.info(f"Channel '{channel.title}' (ID: {channel.channel_id}) upserted successfully.")
            return channel

        except Exception as e:
            self._session.rollback()
            logger.error(f"Failed to upsert channel '{channel_id}': {e}")
            raise

    def update_video(self, video_schema: VideoSchema) -> None:
        """
        Updates video information in the database, including relationships with tags.

        Args:
            video_schema (VideoSchema): The schema containing updated video data.
            channel_id (str): The ID of the channel to which the video belongs.

        Description:
            Updates the existing video record with new data, such as title, description, view count, etc.
            If tags are provided, it updates the relationship between the video and its tags.
            Also sets the `last_update` field to the current timestamp.
        """
        video: Video = self._session.query(Video).filter_by(video_id=video_schema.id).first()
        if video:
            # Update video attributes
            video.title = video_schema.title
            video.description = video_schema.description
            video.url = video_schema.url
            video.duration = video_schema.duration or video.duration
            video.view_count = video_schema.view_count
            video.like_count = video_schema.like_count
            video.comment_count = video_schema.commentCount
            video.upload_date = (
                datetime.fromtimestamp(video_schema.timestamp) if video_schema.timestamp else video.upload_date
            )
            video.defaultaudiolanguage = video_schema.defaultAudioLanguage
            video.last_update = datetime.now().replace(microsecond=0)

            # Update tags if provided
            if video_schema.tags:
                self.bulk_add_tags(video_schema.tags)
                # Retrieve all matching tags
                existing_tag_ids = {
                    tag.id for tag in self._session.query(Tag).filter(Tag.name.in_(video_schema.tags)).all()
                }
                # Delete existing tag relationships
                self._session.query(VideoTag).filter(VideoTag.video_id == video.id).delete(synchronize_session="fetch")
                # Add new tag relationships
                for tag_id in existing_tag_ids:
                    self._session.add(VideoTag(video_id=video.id, tag_id=tag_id))

            self.commit()
            # logger.debug(f"Updated video '{video.title}' (ID: {video.video_id}).")
        else:
            logger.error(f"Video with ID {video_schema.id} not found in the database.")

    def update_video_path(self, video_id: UUID, video_path: Path) -> None:
        """
        Updates the file path where the video is stored.

        Args:
            video_id (UUID): The unique identifier for the video to update.
            video_path (Path): The new file path for the video.

        Description:
            This method updates the storage path of a video in the database. If the video with the specified
            ID exists, its 'video_path' attribute is updated to the new path. The method commits the change
            to the database. If the video does not exist, it logs a warning.
        """
        video: Video = self._session.query(Video).filter_by(id=video_id).first()
        if video:
            video.video_path = str(video_path)
            self._session.commit()
        else:
            logger.warning(f"Video with ID {video_id} not found.")

    def update_thumbnail_path(self, video_id: UUID, thumbnail_url: str, thumbnail_path: Path) -> None:
        """
        Updates the storage path for a specific video thumbnail.

        Args:
            video_id (UUID): The unique identifier of the video associated with the thumbnail.
            thumbnail_url (str): The URL of the thumbnail to update.
            thumbnail_path (Path): The new file path where the thumbnail should be stored.

        Description:
            This method finds a thumbnail by its associated video ID and URL. If the thumbnail is found,
            its 'thumbnail_path' is updated to the new specified path, and the change is committed to the
            database. If no thumbnail matches the criteria, it logs a warning message indicating that the
            thumbnail could not be found.
        """
        thumbnail: Thumbnail = self._session.query(Thumbnail).filter_by(video_id=video_id, url=thumbnail_url).first()
        if thumbnail:
            thumbnail.thumbnail_path = str(thumbnail_path)
            self._session.commit()
        else:
            logger.warning(f"Thumbnail not found for video ID {video_id} with URL {thumbnail_url}.")

    def set_video_as_invalid(self, video_id: str) -> None:
        """
        Marks a video as invalid by setting its like count to -1.

        Args:
            video_id (str): The unique identifier of the video to mark as invalid.

        Description:
            This method searches for a video by its unique video ID. If the video is found,
            it sets the like count to -1 to mark it as invalid, and commits the change to the
            database. If the video is not found, it logs an error message indicating that the
            video could not be found.
        """
        video: Video = self._session.query(Video).filter_by(video_id=video_id).first()
        if video:
            video.like_count = -1
            self.commit()
        else:
            logger.error(f"Video with ID {video_id} not found in the database.")

    def delete_video(self, video_id: UUID):
        """
        Deletes a video from the database by its unique identifier.

        Args:
            video_id (UUID): The unique identifier of the video to be deleted.
        """
        video: Video = self._session.get(Video, str(video_id))
        if video:
            self._session.delete(video)
            self.commit()
        else:
            logger.warning(f"Video with ID {video_id} not found.")

    def reset_all_invalid_videos(self) -> None:
        """
        Resets the like count for all videos that have been marked as invalid in the database.

        Description:
            This method finds all videos in the database with a like count of -1, indicating they have
            been marked as invalid or erroneous in some way. It resets their like count to 0 to clear
            the invalid marker and commits these changes to the database. This operation helps in
            maintaining data integrity and cleaning up data flags that might have been set due to
            processing errors or other conditions. It logs the total number of videos updated to
            provide feedback on the scope of the operation.
        """
        videos: list[Video] = self._session.query(Video).filter(Video.like_count == -1).all()
        for video in videos:
            video.like_count = 0  # Reset the failure marker to a neutral/initial value
        self._session.commit()
        logger.info(f"Reset invalid markers for {len(videos)} videos.")

    def bulk_add_tags(self, tags: list[str]) -> None:
        """
        Adds multiple tags to the database if they do not already exist.

        Description:
            This method performs a bulk addition of tags to the database. It first retrieves all existing
            tags to ensure that no duplicates are created. It then filters out any tags already present
            in the database and adds only the new, unique tags. This approach minimizes database writes
            and ensures efficiency in handling large sets of tag data. If any integrity errors occur
            during the process (e.g., due to concurrent modifications), the transaction is rolled back,
            and an error is logged.

        Parameters:
            tags (list[str]): A list of tag names to be added to the database.

        Raises:
            IntegrityError: If a database integrity issue occurs during the tag addition process.
        """
        existing_tags: list[Tag] = self._session.query(Tag).filter(Tag.name.in_(tags)).all()
        existing_tag_names = {tag.name for tag in existing_tags}

        # Ensure new tags are unique before adding
        unique_new_tags = set(tags) - existing_tag_names
        new_tags = [Tag(name=tag_name) for tag_name in unique_new_tags]

        if new_tags:
            try:
                self._session.bulk_save_objects(new_tags)
                self.commit()
            except IntegrityError as e:
                self._session.rollback()  # Rollback transaction in case of an error
                logger.error(f"Error during bulk add tags: {e}")
