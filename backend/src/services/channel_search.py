from typing import List, Dict, Any, Optional
import logging

from src.api.youtube_client import YouTubeClient
from src.api.quota_manager import QuotaManager
from src.services.cache_service import CacheService
from src.services.channel_filter import ChannelFilter
from src.services.database_service import db_service

logger = logging.getLogger(__name__)


class ChannelSearchService:
    """チャンネル検索オーケストレーター"""

    # デフォルト検索キーワード
    DEFAULT_KEYWORDS = [
        "ゲーム実況",
        "ゲーム配信",
        "生配信",
        "ライブ配信",
        "マインクラフト",
        "APEX",
        "ポケモン",
        "スプラトゥーン",
        "原神",
    ]

    def __init__(
        self,
        youtube_client: Optional[YouTubeClient] = None,
        quota_manager: Optional[QuotaManager] = None,
        cache_service: Optional[CacheService] = None,
        channel_filter: Optional[ChannelFilter] = None,
    ):
        """
        初期化

        Args:
            youtube_client: YouTubeクライアント
            quota_manager: クォータマネージャー
            cache_service: キャッシュサービス
            channel_filter: チャンネルフィルター
        """
        self.youtube = youtube_client or YouTubeClient()
        self.quota_manager = quota_manager or QuotaManager()
        self.cache = cache_service or CacheService()
        self.filter = channel_filter or ChannelFilter()

    def search_channels(
        self,
        keywords: Optional[List[str]] = None,
        published_after: str = "2024-01-01T00:00:00Z",
        max_results_per_keyword: int = 50,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        チャンネルを検索

        Args:
            keywords: 検索キーワードリスト（指定がない場合はデフォルト使用）
            published_after: 公開日以降（ISO 8601形式）
            max_results_per_keyword: キーワードあたりの最大取得件数
            use_cache: キャッシュを使用するか

        Returns:
            {
                "channels": [チャンネル情報リスト],
                "total_count": 合計件数,
                "quota_used": 使用クォータ,
                "cached": キャッシュヒット数
            }
        """
        keywords = keywords or self.DEFAULT_KEYWORDS
        all_channel_ids = set()
        quota_used_in_search = 0
        cached_count = 0

        logger.info(f"Starting channel search: keywords={len(keywords)}, max_results={max_results_per_keyword}")

        # 各キーワードで動画検索を実行
        for keyword in keywords:
            # クォータチェック
            if self.quota_manager.is_quota_exceeded():
                logger.warning("Quota exceeded, stopping search")
                break

            # キャッシュチェック
            if use_cache:
                cached_ids = self.cache.get_search_result(keyword, published_after)
                if cached_ids:
                    all_channel_ids.update(cached_ids)
                    cached_count += 1
                    logger.info(f"Cache HIT for keyword: '{keyword}', {len(cached_ids)} channels")
                    continue

            # YouTube API検索実行
            try:
                channel_ids = self._search_videos_for_keyword(
                    keyword, published_after, max_results_per_keyword
                )
                all_channel_ids.update(channel_ids)
                quota_used_in_search += 100  # search.list = 100 units

                # 検索結果をキャッシュ
                if use_cache:
                    self.cache.set_search_result(keyword, published_after, channel_ids)

                logger.info(f"Searched keyword: '{keyword}', found {len(channel_ids)} unique channels")

            except Exception as e:
                logger.error(f"Failed to search keyword '{keyword}': {e}")
                continue

        # チャンネルIDを重複排除
        unique_channel_ids = list(all_channel_ids)
        logger.info(f"Total unique channels found: {len(unique_channel_ids)}")

        # チャンネル詳細を取得
        channels = self._get_channel_details(unique_channel_ids, use_cache)
        quota_used_in_details = len(unique_channel_ids) // 50 + (1 if len(unique_channel_ids) % 50 else 0)

        # フィルタリング
        filtered_channels = self.filter.filter_channels(channels)

        # データベースに保存（非同期タスクとして実行）
        self._save_channels_to_db(filtered_channels, keywords or self.DEFAULT_KEYWORDS)

        # クォータ使用量を記録
        total_quota_used = quota_used_in_search + quota_used_in_details
        self.quota_manager.add_quota(total_quota_used)

        logger.info(
            f"Search complete: total={len(unique_channel_ids)}, "
            f"filtered={len(filtered_channels)}, quota_used={total_quota_used}"
        )

        return {
            "channels": filtered_channels,
            "total_count": len(filtered_channels),
            "quota_used": total_quota_used,
            "cached_keywords": cached_count,
        }

    def _save_channels_to_db(self, channels: List[Dict[str, Any]], keywords: List[str]):
        """チャンネルをデータベースに保存（同期的に実行）"""
        import asyncio

        async def save():
            for channel in channels:
                try:
                    await db_service.save_channel(channel, keywords)
                except Exception as e:
                    logger.error(f"Failed to save channel {channel.get('id')}: {e}")

        try:
            # 新しいイベントループを作成して実行（uvloop互換）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(save())
            finally:
                loop.close()
            logger.info(f"Saved {len(channels)} channels to database")
        except Exception as e:
            logger.error(f"Failed to save channels to database: {e}", exc_info=True)

    def _search_videos_for_keyword(
        self, keyword: str, published_after: str, max_results: int
    ) -> List[str]:
        """
        キーワードで動画検索してチャンネルIDを抽出

        Args:
            keyword: 検索キーワード
            published_after: 公開日以降
            max_results: 最大取得件数

        Returns:
            チャンネルIDリスト
        """
        channel_ids = set()
        page_token = None
        fetched = 0

        while fetched < max_results:
            remaining = min(50, max_results - fetched)
            response = self.youtube.search_videos(
                keyword=keyword,
                published_after=published_after,
                max_results=remaining,
                page_token=page_token,
            )

            # チャンネルIDを抽出
            ids = self.youtube.extract_channel_ids_from_search(response)
            channel_ids.update(ids)
            fetched += len(response.get("items", []))

            # 次のページトークンを取得
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return list(channel_ids)

    def _get_channel_details(
        self, channel_ids: List[str], use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        チャンネル詳細情報を取得（バッチ処理）

        優先順位:
        1. Redisキャッシュから取得
        2. データベースから取得（既存チャンネル）
        3. YouTube APIから取得（新規チャンネルのみ）

        Args:
            channel_ids: チャンネルIDリスト
            use_cache: キャッシュを使用するか

        Returns:
            チャンネル情報リスト
        """
        import asyncio

        channels = []
        remaining_ids = channel_ids.copy()

        # 1. Redisキャッシュから取得
        if use_cache:
            cached_channels = self.cache.get_channels_batch(channel_ids)
            channels.extend(cached_channels.values())
            remaining_ids = [cid for cid in channel_ids if cid not in cached_channels]
            logger.info(f"Redis cache: {len(cached_channels)} hits, {len(remaining_ids)} misses")

        # 2. データベースから既存チャンネルを取得
        db_channels_dict = {}
        if remaining_ids:
            try:
                # 新しいイベントループを作成して実行（uvloop互換）
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    db_channels_dict = loop.run_until_complete(
                        db_service.get_channels_by_ids(remaining_ids)
                    )
                finally:
                    loop.close()

                # DB形式からAPI形式に変換
                for channel_id, db_channel in db_channels_dict.items():
                    api_format = db_service.db_channel_to_api_format(db_channel)
                    channels.append(api_format)
                    # Redisキャッシュにも保存
                    if use_cache:
                        self.cache.set_channel(channel_id, api_format)

                # DBから取得できたIDを除外
                remaining_ids = [cid for cid in remaining_ids if cid not in db_channels_dict]
                logger.info(f"Database: {len(db_channels_dict)} hits, {len(remaining_ids)} new channels")
            except Exception as e:
                logger.error(f"Failed to fetch from database: {e}", exc_info=True)

        # 3. 新規チャンネルのみYouTube APIから取得
        if remaining_ids:
            logger.info(f"Fetching {len(remaining_ids)} new channels from YouTube API")
            for i in range(0, len(remaining_ids), 50):
                batch_ids = remaining_ids[i : i + 50]
                batch_channels = self.youtube.get_channels_by_ids(batch_ids)
                channels.extend(batch_channels)

                # キャッシュに保存
                if use_cache:
                    self.cache.set_channels_batch(batch_channels)
        else:
            logger.info("All channels found in cache/database, no API call needed!")

        return channels

    def get_channel_by_id(self, channel_id: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        チャンネルIDから詳細情報を取得

        Args:
            channel_id: チャンネルID
            use_cache: キャッシュを使用するか

        Returns:
            チャンネル情報（存在しない場合はNone）
        """
        # キャッシュチェック
        if use_cache:
            cached = self.cache.get_channel(channel_id)
            if cached:
                return cached

        # APIから取得
        channels = self.youtube.get_channels_by_ids([channel_id])
        if channels:
            channel = channels[0]
            if use_cache:
                self.cache.set_channel(channel_id, channel)
            return channel

        return None
