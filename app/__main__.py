from loguru import logger

from app.const import channels_list
from app.db.data_table import Channel
from app.integrations.ytapi import YTApiClient
from app.integrations.ytdlp import YTChannelDownloader
from app.schema import ChannelAPIInfoSchema, ChannelInfoSchema
from app.service.yt_monitor import YTMonitorService

# 1
downloader = YTChannelDownloader("https://www.youtube.com/@BorisYulin")
# 1.1
# with open("yt-dlp_response.json", 'w', encoding='utf-8') as f:
#     json.dump(downloader._get_channel_data(channels_list["channels"][0]), fp=f, ensure_ascii=False, indent=4)
# 1.2
ytdlp_channel_info: ChannelInfoSchema = downloader.get_channel_info()
logger.debug(f"ytdlp_channel_info: {ytdlp_channel_info}")
# 1.2
# video_list, channel_id = downloader.get_video_list()
# new_videos, old_videos = downloader.filter_new_old(video_list, channel_id)

# 2
downloader = YTApiClient()
# 2.1
ytapi_channel_info: ChannelAPIInfoSchema = downloader.get_channel_info([ytdlp_channel_info.channel_id])[0]
logger.debug(f"ytapi_channel_info: {ytapi_channel_info}")
# 2.2
# print(downloader.get_video_info(["QpwJEYGCngI"]))
# downloader.update_video_info(["QpwJEYGCngI"])
# downloader.update_missing_video_info()

# 3
# downloader = YTDownloader()
# for i in range(500):
#     logger.debug(f"Step №{i+1}")
#     downloader.update_video_formats()

# 4
monitor = YTMonitorService(channels_list["channels"])
channel_info: Channel = monitor._combine_channel_info(ytdlp_channel_info, ytapi_channel_info)
logger.debug(f"channel_info: {channel_info}")
# new_videos = monitor.monitor_channels_for_newold_videos()
# logger.debug(f"new_videos: {len(new_videos)}")
monitor.run()
