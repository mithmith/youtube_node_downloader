import os
import sys
from functools import lru_cache
from pathlib import Path

from loguru import logger as log
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_host: str = "localhost"
    app_port: int = 9191

    channels_list_path: str = "channels_list.json"
    storage_path: str = "/mnt/volume"
    video_download_path: str = "videos"
    shorts_download_path: str = "shorts"
    thumbnail_download_path: str = "thumbnails"

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "youtube_db"
    db_schema: str = "youtube"
    db_username: str = "you_tube_db_user"
    db_password: str = "you_tube_db_password"

    monitor_new: bool = True
    monitor_history: bool = False
    monitor_video_formats: bool = False
    run_tg_bot: bool = True
    run_tg_bot_shorts_publish: bool = False

    youtube_api_key: str = "youtube_key"
    youtube_secret_json: str = ""
    youtube_service_secret_json: str = ""

    tg_bot_token: str = "TELEGRAM_BOT_TOKEN"
    tg_group_id: str = "group_id"
    tg_admin_id: int = 0
    tg_new_video_template: Path = "./templates/new_video.md"
    tg_shorts_template: Path = "./templates/shorts.md"
    tg_new_video_template_default: Path = "./templates/new_video.md"
    tg_shorts_template_default: Path = "./templates/shorts.md"

    use_proxy: bool = False
    use_ssh_tunnel: bool = False
    ssh_host: str = "localhost"
    ssh_port: int = 22
    ssh_user: str = "root"
    ssh_private_key: str = "/root/.ssh/id_rsa"

    log_lvl: str = "DEBUG"
    log_dir: str = "logs"
    log_to_file: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_username}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tg_new_video_template = Path(self.tg_new_video_template).resolve()
        self.tg_shorts_template = Path(self.tg_shorts_template).resolve()
        self.tg_new_video_template_default = Path(self.tg_new_video_template_default).resolve()
        self.tg_shorts_template_default = Path(self.tg_shorts_template_default).resolve()


@lru_cache()
def get_logger(log_lvl: str, log_dir: str, log_to_file: bool):
    log_format_console = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SS}</green> "
        "| <level>{level:<8}</level> "
        "| <cyan>{file.name}:{line}</cyan> - <level>{message}</level>"
    )
    log_format_file = "{time:YYYY-MM-DD HH:mm:ss.SS} | {level:<8} | {file.name}:{line} - {message}"

    log.remove()
    log.add(sys.stderr, level=log_lvl, format=log_format_console, colorize=True, enqueue=True)
    if log_to_file:
        os.makedirs(log_dir, exist_ok=True)
        log.add(  # Example log file name: logs/log_2024-02-13.log
            f"{log_dir}/log_{{time:YYYY-MM-DD}}.log",
            level="DEBUG",
            format=log_format_file,
            rotation="1 day",
            retention="30 days",
            compression="zip",
            enqueue=True,
        )
    return log


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
logger = get_logger(settings.log_lvl, settings.log_dir, settings.log_to_file)
