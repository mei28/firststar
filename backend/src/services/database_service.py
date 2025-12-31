import asyncpg
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from src.config.settings import settings
from src.models.db_channel import CREATE_CHANNELS_TABLE_SQL

logger = logging.getLogger(__name__)


class DatabaseService:
    """PostgreSQLデータベースサービス"""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or getattr(settings, 'database_url', None)
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """データベース接続プールを作成"""
        if not self.database_url:
            logger.warning("DATABASE_URL not set, skipping database connection")
            return

        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60,
            )
            logger.info("Database connection pool created")

            # テーブル作成
            await self.init_tables()
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            self.pool = None

    async def disconnect(self):
        """データベース接続を閉じる"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

    async def init_tables(self):
        """テーブルを初期化"""
        if not self.pool:
            return

        async with self.pool.acquire() as conn:
            await conn.execute(CREATE_CHANNELS_TABLE_SQL)
            logger.info("Database tables initialized")

    @asynccontextmanager
    async def get_connection(self):
        """データベース接続を取得"""
        if not self.pool:
            yield None
            return

        async with self.pool.acquire() as conn:
            yield conn

    async def save_channel(self, channel_data: Dict[str, Any], keywords: List[str]) -> bool:
        """チャンネルを保存（既存の場合は更新）"""
        if not self.pool:
            return False

        try:
            async with self.pool.acquire() as conn:
                # 既存チェック
                existing = await conn.fetchrow(
                    "SELECT id, search_keywords FROM channels WHERE id = $1",
                    channel_data["id"]
                )

                now = datetime.now(timezone.utc)

                if existing:
                    # 更新：キーワードをマージ
                    merged_keywords = list(set(existing["search_keywords"] or []) | set(keywords))

                    await conn.execute(
                        """
                        UPDATE channels SET
                            title = $2,
                            description = $3,
                            custom_url = $4,
                            thumbnail_url = $5,
                            country = $6,
                            view_count = $7,
                            subscriber_count = $8,
                            hidden_subscriber_count = $9,
                            video_count = $10,
                            activity_score = $11,
                            last_updated_at = $12,
                            search_keywords = $13
                        WHERE id = $1
                        """,
                        channel_data["id"],
                        channel_data["snippet"]["title"],
                        channel_data["snippet"].get("description", ""),
                        channel_data["snippet"].get("customUrl"),
                        channel_data["snippet"]["thumbnails"]["medium"]["url"],
                        channel_data["snippet"].get("country"),
                        int(channel_data["statistics"].get("viewCount", 0)),
                        int(channel_data["statistics"]["subscriberCount"]) if channel_data["statistics"].get("subscriberCount") else None,
                        channel_data["statistics"].get("hiddenSubscriberCount", False),
                        int(channel_data["statistics"].get("videoCount", 0)),
                        channel_data.get("activity_score"),
                        now,
                        merged_keywords,
                    )
                    logger.debug(f"Updated channel: {channel_data['id']}")
                else:
                    # 新規挿入
                    published_at = datetime.fromisoformat(
                        channel_data["snippet"]["publishedAt"].replace("Z", "+00:00")
                    )

                    await conn.execute(
                        """
                        INSERT INTO channels (
                            id, title, description, custom_url, published_at,
                            thumbnail_url, country, view_count, subscriber_count,
                            hidden_subscriber_count, video_count, activity_score,
                            first_discovered_at, last_updated_at, search_keywords
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                        """,
                        channel_data["id"],
                        channel_data["snippet"]["title"],
                        channel_data["snippet"].get("description", ""),
                        channel_data["snippet"].get("customUrl"),
                        published_at,
                        channel_data["snippet"]["thumbnails"]["medium"]["url"],
                        channel_data["snippet"].get("country"),
                        int(channel_data["statistics"].get("viewCount", 0)),
                        int(channel_data["statistics"]["subscriberCount"]) if channel_data["statistics"].get("subscriberCount") else None,
                        channel_data["statistics"].get("hiddenSubscriberCount", False),
                        int(channel_data["statistics"].get("videoCount", 0)),
                        channel_data.get("activity_score"),
                        now,
                        now,
                        keywords,
                    )
                    logger.debug(f"Inserted new channel: {channel_data['id']}")

                return True

        except Exception as e:
            logger.error(f"Failed to save channel: {e}")
            return False

    async def get_all_channels(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "activity_score DESC"
    ) -> List[Dict[str, Any]]:
        """すべてのチャンネルを取得"""
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    f"""
                    SELECT * FROM channels
                    ORDER BY {order_by}
                    LIMIT $1 OFFSET $2
                    """,
                    limit,
                    offset
                )

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get channels: {e}")
            return []

    async def get_channel_by_id(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """IDでチャンネルを取得"""
        if not self.pool:
            return None

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM channels WHERE id = $1",
                    channel_id
                )

                return dict(row) if row else None

        except Exception as e:
            logger.error(f"Failed to get channel: {e}")
            return None

    async def get_channels_by_ids(self, channel_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """複数のチャンネルをIDで一括取得"""
        if not self.pool or not channel_ids:
            return {}

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM channels WHERE id = ANY($1)",
                    channel_ids
                )

                # {channel_id: channel_data} の辞書で返す
                return {row["id"]: dict(row) for row in rows}

        except Exception as e:
            logger.error(f"Failed to get channels by ids: {e}")
            return {}

    def db_channel_to_api_format(self, db_channel: Dict[str, Any]) -> Dict[str, Any]:
        """データベース形式からYouTube API形式に変換"""
        return {
            "kind": "youtube#channel",
            "etag": "",
            "id": db_channel["id"],
            "snippet": {
                "title": db_channel["title"],
                "description": db_channel["description"],
                "customUrl": db_channel["custom_url"],
                "publishedAt": db_channel["published_at"].isoformat() + "Z" if db_channel.get("published_at") else None,
                "thumbnails": {
                    "default": {"url": db_channel["thumbnail_url"], "width": 88, "height": 88},
                    "medium": {"url": db_channel["thumbnail_url"], "width": 240, "height": 240},
                    "high": {"url": db_channel["thumbnail_url"], "width": 800, "height": 800},
                },
                "country": db_channel.get("country"),
            },
            "contentDetails": {
                "relatedPlaylists": {
                    "likes": "",
                    "uploads": f"UU{db_channel['id'][2:]}" if db_channel["id"].startswith("UC") else "",
                }
            },
            "statistics": {
                "viewCount": str(db_channel.get("view_count", 0)),
                "subscriberCount": str(db_channel["subscriber_count"]) if db_channel.get("subscriber_count") else None,
                "hiddenSubscriberCount": db_channel.get("hidden_subscriber_count", False),
                "videoCount": str(db_channel.get("video_count", 0)),
            },
            "activity_score": db_channel.get("activity_score"),
        }

    async def get_stats(self) -> Dict[str, Any]:
        """データベース統計を取得"""
        if not self.pool:
            return {"total_channels": 0, "database_connected": False}

        try:
            async with self.pool.acquire() as conn:
                total = await conn.fetchval("SELECT COUNT(*) FROM channels")
                latest = await conn.fetchrow(
                    "SELECT last_updated_at FROM channels ORDER BY last_updated_at DESC LIMIT 1"
                )

                return {
                    "total_channels": total,
                    "database_connected": True,
                    "latest_update": latest["last_updated_at"].isoformat() if latest else None,
                }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"total_channels": 0, "database_connected": False, "error": str(e)}


# グローバルインスタンス
db_service = DatabaseService()
