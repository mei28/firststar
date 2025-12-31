import redis
import json
import logging
from typing import Optional, Any, List
from datetime import timedelta

from src.config.settings import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redisキャッシュサービス"""

    # TTL設定（秒）
    CHANNEL_TTL = 24 * 60 * 60  # 24時間
    SEARCH_TTL = 6 * 60 * 60  # 6時間
    CATEGORY_TTL = 7 * 24 * 60 * 60  # 7日間

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        初期化

        Args:
            redis_client: Redisクライアント（指定がない場合は新規作成）
        """
        if redis_client is None:
            self.redis = redis.from_url(settings.redis_url, decode_responses=True)
        else:
            self.redis = redis_client

    def _make_channel_key(self, channel_id: str) -> str:
        """チャンネルキャッシュキーを生成"""
        return f"channel:{channel_id}"

    def _make_search_key(self, keyword: str, published_after: str) -> str:
        """検索キャッシュキーを生成"""
        return f"search:{keyword}:{published_after}"

    def get_channel(self, channel_id: str) -> Optional[dict]:
        """
        チャンネル情報をキャッシュから取得

        Args:
            channel_id: チャンネルID

        Returns:
            チャンネル情報（存在しない場合はNone）
        """
        try:
            key = self._make_channel_key(channel_id)
            data = self.redis.get(key)
            if data:
                logger.debug(f"Cache HIT: channel:{channel_id}")
                return json.loads(data)
            logger.debug(f"Cache MISS: channel:{channel_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get channel from cache: {e}")
            return None

    def set_channel(self, channel_id: str, channel_data: dict, ttl: Optional[int] = None):
        """
        チャンネル情報をキャッシュに保存

        Args:
            channel_id: チャンネルID
            channel_data: チャンネル情報
            ttl: 有効期限（秒）、デフォルトは24時間
        """
        try:
            key = self._make_channel_key(channel_id)
            ttl = ttl or self.CHANNEL_TTL
            self.redis.setex(key, ttl, json.dumps(channel_data))
            logger.debug(f"Cached channel: {channel_id}, TTL={ttl}s")
        except Exception as e:
            logger.error(f"Failed to cache channel: {e}")

    def get_channels_batch(self, channel_ids: List[str]) -> dict[str, dict]:
        """
        複数のチャンネル情報をキャッシュから取得

        Args:
            channel_ids: チャンネルIDリスト

        Returns:
            {channel_id: channel_data}の辞書
        """
        results = {}
        for channel_id in channel_ids:
            data = self.get_channel(channel_id)
            if data:
                results[channel_id] = data
        return results

    def set_channels_batch(self, channels: List[dict], ttl: Optional[int] = None):
        """
        複数のチャンネル情報をキャッシュに保存

        Args:
            channels: チャンネル情報リスト（各要素に'id'キーが必要）
            ttl: 有効期限（秒）
        """
        for channel in channels:
            channel_id = channel.get("id")
            if channel_id:
                self.set_channel(channel_id, channel, ttl)

    def get_search_result(self, keyword: str, published_after: str) -> Optional[List[str]]:
        """
        検索結果（チャンネルIDリスト）をキャッシュから取得

        Args:
            keyword: 検索キーワード
            published_after: 公開日以降

        Returns:
            チャンネルIDリスト（存在しない場合はNone）
        """
        try:
            key = self._make_search_key(keyword, published_after)
            data = self.redis.get(key)
            if data:
                logger.debug(f"Cache HIT: search:{keyword}")
                return json.loads(data)
            logger.debug(f"Cache MISS: search:{keyword}")
            return None
        except Exception as e:
            logger.error(f"Failed to get search result from cache: {e}")
            return None

    def set_search_result(
        self, keyword: str, published_after: str, channel_ids: List[str], ttl: Optional[int] = None
    ):
        """
        検索結果をキャッシュに保存

        Args:
            keyword: 検索キーワード
            published_after: 公開日以降
            channel_ids: チャンネルIDリスト
            ttl: 有効期限（秒）、デフォルトは6時間
        """
        try:
            key = self._make_search_key(keyword, published_after)
            ttl = ttl or self.SEARCH_TTL
            self.redis.setex(key, ttl, json.dumps(channel_ids))
            logger.debug(f"Cached search result: {keyword}, count={len(channel_ids)}, TTL={ttl}s")
        except Exception as e:
            logger.error(f"Failed to cache search result: {e}")

    def clear_all(self):
        """全キャッシュをクリア（テスト用）"""
        try:
            # パターンマッチングで削除
            for pattern in ["channel:*", "search:*"]:
                keys = self.redis.keys(pattern)
                if keys:
                    self.redis.delete(*keys)
            logger.info("All cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")

    def get_cache_stats(self) -> dict:
        """キャッシュ統計を取得"""
        try:
            channel_keys = self.redis.keys("channel:*")
            search_keys = self.redis.keys("search:*")

            return {
                "channel_count": len(channel_keys),
                "search_count": len(search_keys),
                "total_keys": len(channel_keys) + len(search_keys),
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"channel_count": 0, "search_count": 0, "total_keys": 0}
