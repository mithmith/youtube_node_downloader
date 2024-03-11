from app.const import channels_list
from app.service.ytapi import YTApiService
from app.service.ytdlp import YTDownloader

test_channels_list = {"channels": ["https://www.youtube.com/@bolsheviktv3342"]}

# downloader = YTDownloader()
# downloader.update_channels_metadata(channels_list["channels"])

downloader = YTApiService()
downloader.update_missing_video_info()
