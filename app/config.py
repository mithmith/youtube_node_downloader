from functools import lru_cache

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
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
