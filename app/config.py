import os
import sys
from functools import lru_cache

from loguru import logger as log
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_host: str = "localhost"
    app_port: int = 9191

    storage_path: str = "/mnt/volume"
    video_download_path: str = "videos"
    shorts_download_path: str = "shorts"
    thumbnail_download_path: str = "videos/thumbnail"

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "peer_tube_db"
    db_schema: str = "youtube"
    db_username: str = "peer_tube_user"
    db_password: str = "peer_tube_password"

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

    ssh_host: str = "localhost"
    ssh_port: int = 22
    ssh_user: str = "root"
    ssh_private_key: str = "/root/.ssh/id_rsa"

    log_lvl: str = "INFO"
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


@lru_cache()
def get_logger(settings: Settings):
    log.remove()
    log.add(sys.stderr, level=settings.log_lvl, format="{time} | {level} | {message}", enqueue=True)
    if settings.log_to_file:
        os.makedirs(settings.log_dir, exist_ok=True)
        log.add(  # Example log file name: logs/log_2024-02-13.log
            f"{settings.log_dir}/log_{{time:YYYY-MM-DD}}.log",
            level="DEBUG",
            format="{time} | {level} | {message}",
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
logger = get_logger(settings)
