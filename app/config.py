from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_host: str = "localhost"
    app_port: int = 9091
    storage_path: str = "/mnt/volume"

    your_username: str = "name"
    your_password: str = "password"

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "peer_tube"
    db_schema: str = "youtube"
    db_username: str = "postgres"
    db_password: str = "postgres"

    video_download_path: str = "/video/download"
    thumbnail_download_path: str = "/video/download/thumbnail"

    youtube_api_key: str = "youtube_key"
    youtube_secret_json: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_username}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
