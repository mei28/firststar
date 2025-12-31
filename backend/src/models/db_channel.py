from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DBChannel(BaseModel):
    """データベース用チャンネルモデル"""

    id: str
    title: str
    description: str
    custom_url: Optional[str] = None
    published_at: datetime
    thumbnail_url: str
    country: Optional[str] = None

    view_count: int
    subscriber_count: Optional[int] = None
    hidden_subscriber_count: bool
    video_count: int

    activity_score: Optional[float] = None

    # メタデータ
    first_discovered_at: datetime
    last_updated_at: datetime
    search_keywords: list[str] = []  # このチャンネルを発見したキーワード

    class Config:
        from_attributes = True


# SQLAlchemy用のテーブル定義は必要に応じて追加
CREATE_CHANNELS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS channels (
    id VARCHAR(255) PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    custom_url VARCHAR(255),
    published_at TIMESTAMPTZ NOT NULL,
    thumbnail_url TEXT NOT NULL,
    country VARCHAR(10),

    view_count BIGINT DEFAULT 0,
    subscriber_count INT,
    hidden_subscriber_count BOOLEAN DEFAULT FALSE,
    video_count INT DEFAULT 0,

    activity_score FLOAT,

    first_discovered_at TIMESTAMPTZ NOT NULL,
    last_updated_at TIMESTAMPTZ NOT NULL,
    search_keywords TEXT[]
);

CREATE INDEX IF NOT EXISTS idx_channels_published_at ON channels(published_at);
CREATE INDEX IF NOT EXISTS idx_channels_subscriber_count ON channels(subscriber_count);
CREATE INDEX IF NOT EXISTS idx_channels_activity_score ON channels(activity_score);
CREATE INDEX IF NOT EXISTS idx_channels_last_updated ON channels(last_updated_at);
"""
