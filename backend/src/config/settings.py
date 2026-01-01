from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    """アプリケーション設定"""

    # YouTube Data API v3 (カンマ区切りで複数設定可能)
    youtube_api_key: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # PostgreSQL (オプション、設定されていればデータ永続化)
    database_url: Optional[str] = None

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # APIクォータ
    quota_daily_limit: int = 10000
    quota_warning_threshold: int = 2000

    # FastAPI
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """CORSオリジンをリストに変換"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def youtube_api_keys(self) -> List[str]:
        """YouTube APIキーをリストに変換（カンマ区切り対応）"""
        return [key.strip() for key in self.youtube_api_key.split(",") if key.strip()]


# グローバル設定インスタンス
settings = Settings()
