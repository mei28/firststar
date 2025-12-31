from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

from src.config.settings import settings

logger = logging.getLogger(__name__)


class YouTubeClient:
    """YouTube Data API v3クライアント"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初期化

        Args:
            api_key: YouTube Data API キー（指定がない場合は設定から取得）
        """
        self.api_key = api_key or settings.youtube_api_key
        self.youtube = build("youtube", "v3", developerKey=self.api_key)
        self._quota_used = 0

    def search_videos(
        self,
        keyword: str,
        published_after: str = "2024-01-01T00:00:00Z",
        max_results: int = 50,
        page_token: Optional[str] = None,
        region_code: str = "JP",
        video_category_id: str = "20",
    ) -> Dict[str, Any]:
        """
        動画検索（search.list: 100 units/call）

        Args:
            keyword: 検索キーワード
            published_after: 公開日以降（ISO 8601形式）
            max_results: 最大取得件数（1-50）
            page_token: ページネーショントークン
            region_code: 地域コード
            video_category_id: 動画カテゴリID（20=Gaming）

        Returns:
            検索結果（items, nextPageToken等）
        """
        try:
            request = self.youtube.search().list(
                part="snippet",
                type="video",
                q=keyword,
                videoCategoryId=video_category_id,
                publishedAfter=published_after,
                regionCode=region_code,
                eventType="completed",  # 過去のライブ配信を含む
                maxResults=max_results,
                order="date",
                pageToken=page_token,
            )
            response = request.execute()
            self._quota_used += 100  # search.listは100 units

            logger.info(
                f"search_videos: keyword='{keyword}', results={len(response.get('items', []))}, "
                f"quota_used={self._quota_used}"
            )

            return response

        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
            if e.resp.status == 403:
                # クォータ超過またはAPIキーエラー
                error_reason = e.error_details[0].get("reason", "unknown")
                if error_reason == "quotaExceeded":
                    raise Exception("APIクォータを超過しました")
                elif error_reason == "rateLimitExceeded":
                    raise Exception("レート制限を超過しました")
            raise

    def get_channels_by_ids(self, channel_ids: List[str]) -> List[Dict[str, Any]]:
        """
        チャンネル詳細をバッチ取得（channels.list: 1 unit/call、最大50件）

        Args:
            channel_ids: チャンネルIDリスト（最大50件）

        Returns:
            チャンネル情報リスト
        """
        if not channel_ids:
            return []

        # 最大50件に制限
        channel_ids = channel_ids[:50]

        try:
            request = self.youtube.channels().list(
                part="snippet,statistics,contentDetails",
                id=",".join(channel_ids),
            )
            response = request.execute()
            self._quota_used += 1  # channels.listは1 unit（50件まで）

            channels = response.get("items", [])
            logger.info(
                f"get_channels_by_ids: requested={len(channel_ids)}, "
                f"returned={len(channels)}, quota_used={self._quota_used}"
            )

            return channels

        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
            raise

    def extract_channel_ids_from_search(self, search_response: Dict[str, Any]) -> List[str]:
        """
        検索結果からチャンネルIDを抽出

        Args:
            search_response: search.listのレスポンス

        Returns:
            チャンネルIDリスト
        """
        channel_ids = []
        for item in search_response.get("items", []):
            channel_id = item["snippet"].get("channelId")
            if channel_id:
                channel_ids.append(channel_id)

        return channel_ids

    @property
    def quota_used(self) -> int:
        """使用したクォータ数を取得"""
        return self._quota_used

    def reset_quota_counter(self):
        """クォータカウンターをリセット"""
        self._quota_used = 0
