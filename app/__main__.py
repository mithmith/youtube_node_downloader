from loguru import logger

from app.const import channels_list
from app.service.ytapi import YTApiService
from app.service.ytdlp import YTDownloader

# # 1
# downloader = YTDownloader()
# downloader.update_channels_metadata(channels_list["channels"])

# # 2.1
# downloader = YTApiService()
# downloader.update_missing_video_info()

# # 2.2
# downloader = YTApiService()
# downloader.update_channels_info()

# 3
downloader = YTDownloader()
for i in range(500):
    logger.debug(f"Step №{i+1}")
    downloader.update_video_formats()
