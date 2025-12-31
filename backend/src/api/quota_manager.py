import redis
from datetime import datetime, timedelta
import logging
from typing import Optional

from src.config.settings import settings

logger = logging.getLogger(__name__)


class QuotaManager:
    """APIクォータ管理"""

    QUOTA_KEY = "youtube_api:quota:used"
    QUOTA_RESET_KEY = "youtube_api:quota:reset_at"

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

    def get_used_quota(self) -> int:
        """現在の使用クォータを取得"""
        try:
            used = self.redis.get(self.QUOTA_KEY)
            return int(used) if used else 0
        except Exception as e:
            logger.error(f"Failed to get quota from Redis: {e}")
            return 0

    def add_quota(self, amount: int) -> int:
        """
        クォータ使用量を追加

        Args:
            amount: 追加するクォータ量

        Returns:
            追加後の合計使用量
        """
        try:
            # クォータを加算
            new_total = self.redis.incrby(self.QUOTA_KEY, amount)

            # 初回設定時、翌日0時(UTC)にリセットされるよう TTL を設定
            ttl = self.redis.ttl(self.QUOTA_KEY)
            if ttl == -1:  # TTLが設定されていない場合
                self._set_daily_expiry()

            logger.info(f"Added quota: +{amount}, total={new_total}")
            return int(new_total)
        except Exception as e:
            logger.error(f"Failed to add quota to Redis: {e}")
            return 0

    def get_remaining_quota(self) -> int:
        """残りクォータを取得"""
        used = self.get_used_quota()
        return max(0, settings.quota_daily_limit - used)

    def is_quota_exceeded(self) -> bool:
        """クォータ超過をチェック"""
        return self.get_used_quota() >= settings.quota_daily_limit

    def is_warning_threshold(self) -> bool:
        """警告閾値に達しているかチェック"""
        remaining = self.get_remaining_quota()
        return remaining <= settings.quota_warning_threshold

    def get_reset_time(self) -> Optional[datetime]:
        """クォータリセット時刻を取得"""
        try:
            ttl = self.redis.ttl(self.QUOTA_KEY)
            if ttl > 0:
                return datetime.utcnow() + timedelta(seconds=ttl)
            return None
        except Exception as e:
            logger.error(f"Failed to get reset time from Redis: {e}")
            return None

    def _set_daily_expiry(self):
        """
        翌日0時(UTC)にキーが自動削除されるようTTLを設定
        """
        now = datetime.utcnow()
        tomorrow = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        seconds_until_reset = int((tomorrow - now).total_seconds())

        self.redis.expire(self.QUOTA_KEY, seconds_until_reset)
        logger.info(f"Set quota expiry: {seconds_until_reset}s until {tomorrow}")

    def reset_quota(self):
        """クォータを手動リセット（テスト用）"""
        try:
            self.redis.delete(self.QUOTA_KEY)
            self.redis.delete(self.QUOTA_RESET_KEY)
            logger.info("Quota manually reset")
        except Exception as e:
            logger.error(f"Failed to reset quota: {e}")

    def get_quota_status(self) -> dict:
        """クォータ状況を取得"""
        used = self.get_used_quota()
        remaining = self.get_remaining_quota()
        reset_time = self.get_reset_time()

        return {
            "used": used,
            "remaining": remaining,
            "limit": settings.quota_daily_limit,
            "warning_threshold": settings.quota_warning_threshold,
            "is_exceeded": self.is_quota_exceeded(),
            "is_warning": self.is_warning_threshold(),
            "reset_at": reset_time.isoformat() if reset_time else None,
        }
