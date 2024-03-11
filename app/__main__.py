from app.const import channels_list
from app.service.ytapi import YTApiService
from app.service.ytdlp import YTDownloader

downloader = YTDownloader()
formats = downloader.get_video_formats("9yvgK99eQps")
print(formats)

# downloader = YTApiService()
# downloader.update_missing_video_info()
