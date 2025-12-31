from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChannelSnippet(BaseModel):
    """チャンネルスニペット情報"""

    title: str
    description: str
    published_at: datetime = Field(alias="publishedAt")
    thumbnails: dict
    country: Optional[str] = None


class ChannelStatistics(BaseModel):
    """チャンネル統計情報"""

    view_count: int = Field(alias="viewCount", default=0)
    subscriber_count: Optional[int] = Field(alias="subscriberCount", default=None)
    hidden_subscriber_count: bool = Field(alias="hiddenSubscriberCount", default=False)
    video_count: int = Field(alias="videoCount", default=0)


class ChannelContentDetails(BaseModel):
    """チャンネルコンテンツ詳細"""

    related_playlists: dict = Field(alias="relatedPlaylists")


class Channel(BaseModel):
    """YouTubeチャンネルモデル"""

    id: str
    snippet: ChannelSnippet
    statistics: ChannelStatistics
    content_details: ChannelContentDetails = Field(alias="contentDetails")
    activity_score: Optional[float] = None

    model_config = {
        "populate_by_name": True,
    }

    @property
    def channel_url(self) -> str:
        """チャンネルURLを生成"""
        return f"https://www.youtube.com/channel/{self.id}"

    @property
    def subscriber_count_display(self) -> str:
        """登録者数の表示用文字列"""
        if self.statistics.hidden_subscriber_count:
            return "非公開"
        if self.statistics.subscriber_count is None:
            return "不明"
        return str(self.statistics.subscriber_count)


class ChannelSearchResult(BaseModel):
    """チャンネル検索結果"""

    channels: list[Channel]
    total_count: int
    quota_used: int
