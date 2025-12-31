from datetime import datetime
from typing import List, Dict, Any
import logging
import re

logger = logging.getLogger(__name__)


class ChannelFilter:
    """チャンネルフィルタリングサービス"""

    # ゲーム関連キーワード
    GAMING_KEYWORDS = [
        # 一般ワード
        "ゲーム", "実況", "配信", "生配信", "ライブ", "プレイ", "攻略",
        # 人気ゲームタイトル
        "マインクラフト", "マイクラ", "Minecraft",
        "APEX", "エーペックス", "Apex",
        "ポケモン", "Pokemon", "ポケットモンスター",
        "原神", "Genshin",
        "スプラトゥーン", "Splatoon",
        "フォートナイト", "Fortnite",
        "モンハン", "Monster Hunter",
        "ストリートファイター", "Street Fighter",
        "ゼルダ", "Zelda",
        "スマブラ", "Smash Bros",
        "FF14", "Final Fantasy",
        "ドラクエ", "Dragon Quest",
        "パズドラ", "モンスト",
        # プラットフォーム
        "Switch", "PS5", "PS4", "Steam", "PC",
        # 配信関連
        "Streamer", "ストリーマー", "Vtuber", "ゲーム実況者",
    ]

    def __init__(
        self,
        published_after: str = "2024-01-01T00:00:00Z",
        max_subscriber_count: int = 2000,
        min_video_count: int = 5,
    ):
        """
        初期化

        Args:
            published_after: チャンネル作成日以降（ISO 8601形式）
            max_subscriber_count: 最大登録者数
            min_video_count: 最小動画本数（活動チャンネル判定）
        """
        self.published_after = datetime.fromisoformat(published_after.replace("Z", "+00:00"))
        self.max_subscriber_count = max_subscriber_count
        self.min_video_count = min_video_count

    def filter_channels(self, channels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        チャンネルリストをフィルタリング

        Args:
            channels: チャンネル情報リスト

        Returns:
            フィルタリング後のチャンネルリスト
        """
        filtered = []
        for channel in channels:
            if self._is_match(channel):
                # 活動度スコアを計算
                channel["activity_score"] = self._calculate_activity_score(channel)
                filtered.append(channel)

        # スコア降順でソート
        filtered.sort(key=lambda x: x.get("activity_score", 0), reverse=True)

        logger.info(
            f"Filtered channels: input={len(channels)}, output={len(filtered)}, "
            f"filters=(published_after={self.published_after.date()}, "
            f"max_subscribers={self.max_subscriber_count}, "
            f"min_videos={self.min_video_count})"
        )

        return filtered

    def _is_match(self, channel: Dict[str, Any]) -> bool:
        """
        チャンネルが条件に合致するかチェック

        Args:
            channel: チャンネル情報

        Returns:
            合致する場合True
        """
        # 1. チャンネル作成日チェック
        if not self._check_published_date(channel):
            return False

        # 2. 登録者数チェック
        if not self._check_subscriber_count(channel):
            return False

        # 3. 動画本数チェック
        if not self._check_video_count(channel):
            return False

        # 4. ゲーム関連コンテンツチェック
        if not self._check_gaming_content(channel):
            return False

        return True

    def _check_published_date(self, channel: Dict[str, Any]) -> bool:
        """チャンネル作成日をチェック"""
        try:
            published_at_str = channel["snippet"]["publishedAt"]
            published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
            return published_at >= self.published_after
        except (KeyError, ValueError) as e:
            logger.warning(f"Failed to parse publishedAt: {e}")
            return False

    def _check_subscriber_count(self, channel: Dict[str, Any]) -> bool:
        """登録者数をチェック"""
        try:
            statistics = channel.get("statistics", {})
            hidden = statistics.get("hiddenSubscriberCount", False)

            # 非公開の場合は一旦通す（後で手動確認）
            if hidden:
                return True

            subscriber_count = statistics.get("subscriberCount")
            if subscriber_count is None:
                return True  # 不明な場合も通す

            return int(subscriber_count) < self.max_subscriber_count
        except (KeyError, ValueError) as e:
            logger.warning(f"Failed to check subscriber count: {e}")
            return True  # エラー時は通す

    def _check_video_count(self, channel: Dict[str, Any]) -> bool:
        """動画本数をチェック（活動チャンネル判定）"""
        try:
            video_count = channel.get("statistics", {}).get("videoCount", 0)
            return int(video_count) >= self.min_video_count
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to check video count: {e}")
            return False

    def _check_gaming_content(self, channel: Dict[str, Any]) -> bool:
        """ゲーム関連コンテンツかチェック"""
        try:
            title = channel["snippet"].get("title", "").lower()
            description = channel["snippet"].get("description", "").lower()

            # タイトルまたは説明文にゲーム関連キーワードが含まれているかチェック
            text = f"{title} {description}"
            for keyword in self.GAMING_KEYWORDS:
                if keyword.lower() in text:
                    return True

            return False
        except KeyError as e:
            logger.warning(f"Failed to check gaming content: {e}")
            return False

    def _calculate_activity_score(self, channel: Dict[str, Any]) -> float:
        """
        チャンネル活動度スコアを計算

        スコア計算要素:
        - 動画投稿頻度（最大30点）
        - ゲームキーワード密度（最大50点）
        - 視聴回数（最大20点）

        Returns:
            0-100のスコア
        """
        score = 0.0

        try:
            statistics = channel.get("statistics", {})
            snippet = channel["snippet"]

            # 動画投稿頻度（週1本以上で満点）
            published_at_str = snippet["publishedAt"]
            published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
            weeks_since_creation = max(1, (datetime.now(published_at.tzinfo) - published_at).days / 7)
            video_count = int(statistics.get("videoCount", 0))
            videos_per_week = video_count / weeks_since_creation
            score += min(30, videos_per_week * 10)

            # ゲームキーワード密度
            title = snippet.get("title", "").lower()
            description = snippet.get("description", "").lower()
            text = f"{title} {description}"
            keyword_count = sum(1 for kw in self.GAMING_KEYWORDS if kw.lower() in text)
            score += min(50, keyword_count * 10)

            # 視聴回数（対数スケール）
            view_count = int(statistics.get("viewCount", 0))
            if view_count > 0:
                import math
                score += min(20, math.log10(view_count + 1) * 2)

        except Exception as e:
            logger.warning(f"Failed to calculate activity score: {e}")

        return round(score, 2)
