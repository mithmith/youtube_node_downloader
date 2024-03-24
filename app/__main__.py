import json

from loguru import logger

from app.const import channels_list
from app.integrations.ytapi import YTApiClient
from app.integrations.ytdlp import YTDownloader
from app.schema import ChannelAPIInfoSchema, ChannelInfoSchema, VideoSchema

# 1
# downloader = YTDownloader()
# 1.1
# with open("yt-dlp_response.json", 'w', encoding='utf-8') as f:
#     json.dump(downloader._get_channel_data(channels_list["channels"][0]), fp=f, ensure_ascii=False, indent=4)
# 1.2
# ytdlp_channel_info: ChannelInfoSchema = downloader.get_channel_info(channels_list["channels"][0])
# 1.2
# video_info: VideoSchema = downloader.get_video_list(channels_list["channels"][0])[0][0]
# print(video_info)
# downloader.update_channels_metadata(channels_list["channels"])

# 2
downloader = YTApiClient()
# 2.1
# ytapi_channel_info: ChannelAPIInfoSchema = downloader.get_channel_info([ytdlp_channel_info.channel_id])[0]
# 2.2
print(downloader.get_video_info(["QpwJEYGCngI"]))
# downloader.update_video_info(["QpwJEYGCngI"])
# downloader.update_missing_video_info()

# # 2.2
# downloader = YTApiService()
# downloader.update_channels_info()

# 3
# downloader = YTDownloader()
# for i in range(500):
#     logger.debug(f"Step №{i+1}")
#     downloader.update_video_formats()
