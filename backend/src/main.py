from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from contextlib import asynccontextmanager
import logging

from src.config.settings import settings
from src.services.channel_search import ChannelSearchService
from src.api.quota_manager import QuotaManager
from src.services.cache_service import CacheService
from src.services.database_service import db_service

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションライフサイクル管理"""
    # 起動時
    logger.info("Starting application...")
    await db_service.connect()
    yield
    # 終了時
    logger.info("Shutting down application...")
    await db_service.disconnect()


# FastAPIアプリケーション
app = FastAPI(
    title="YouTube Channel Finder API",
    description="2024年以降に開始された日本のゲーム配信チャンネルを検索するAPI",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# サービスインスタンス
search_service = ChannelSearchService()
quota_manager = QuotaManager()
cache_service = CacheService()


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "YouTube Channel Finder API",
        "version": "1.0.0",
        "endpoints": {
            "search": "/api/channels/search",
            "get_channel": "/api/channels/{channel_id}",
            "quota_status": "/api/quota/status",
            "cache_clear": "/api/cache/clear",
        },
    }


@app.get("/api/channels/search")
async def search_channels(
    keywords: Optional[List[str]] = Query(
        None,
        description="検索キーワード（未指定の場合はデフォルトキーワード使用）",
    ),
    published_after: str = Query(
        "2024-01-01T00:00:00Z",
        description="チャンネル作成日以降（ISO 8601形式）",
    ),
    max_results_per_keyword: int = Query(
        50,
        ge=1,
        le=50,
        description="キーワードあたりの最大取得件数（1-50）",
    ),
    use_cache: bool = Query(True, description="キャッシュを使用するか"),
):
    """
    チャンネル検索

    - **keywords**: 検索キーワードリスト
    - **published_after**: チャンネル作成日以降
    - **max_results_per_keyword**: キーワードあたりの最大取得件数
    - **use_cache**: キャッシュ使用の有無
    """
    try:
        # クォータチェック
        if quota_manager.is_quota_exceeded():
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "APIクォータを超過しました",
                    "quota_status": quota_manager.get_quota_status(),
                },
            )

        # 検索実行
        result = search_service.search_channels(
            keywords=keywords,
            published_after=published_after,
            max_results_per_keyword=max_results_per_keyword,
            use_cache=use_cache,
        )

        # クォータ状況を追加
        result["quota_status"] = quota_manager.get_quota_status()

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/channels/{channel_id}")
async def get_channel(
    channel_id: str,
    use_cache: bool = Query(True, description="キャッシュを使用するか"),
):
    """
    チャンネルIDから詳細情報を取得

    - **channel_id**: YouTubeチャンネルID
    - **use_cache**: キャッシュ使用の有無
    """
    try:
        channel = search_service.get_channel_by_id(channel_id, use_cache=use_cache)

        if not channel:
            raise HTTPException(
                status_code=404,
                detail=f"Channel not found: {channel_id}",
            )

        return channel

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get channel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/quota/status")
async def get_quota_status():
    """
    APIクォータの使用状況を取得

    Returns:
        - **used**: 使用済みクォータ
        - **remaining**: 残りクォータ
        - **limit**: 1日の上限
        - **warning_threshold**: 警告閾値
        - **is_exceeded**: クォータ超過フラグ
        - **is_warning**: 警告閾値到達フラグ
        - **reset_at**: リセット時刻（ISO 8601形式）
    """
    try:
        status = quota_manager.get_quota_status()
        cache_stats = cache_service.get_cache_stats()
        db_stats = await db_service.get_stats()

        return {
            "quota": status,
            "cache": cache_stats,
            "database": db_stats,
        }

    except Exception as e:
        logger.error(f"Failed to get quota status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/channels/database")
async def get_database_channels(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    order_by: str = Query("activity_score DESC", description="ソート順"),
):
    """
    データベースから保存済みチャンネルを取得

    - **limit**: 取得件数
    - **offset**: オフセット
    - **order_by**: ソート順（例: "activity_score DESC", "subscriber_count DESC"）
    """
    try:
        channels = await db_service.get_all_channels(
            limit=limit,
            offset=offset,
            order_by=order_by
        )

        return {
            "channels": channels,
            "total_count": len(channels),
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"Failed to get database channels: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cache/clear")
async def clear_cache():
    """
    キャッシュを全クリア（テスト・デバッグ用）

    注意: 本番環境では使用を制限することを推奨
    """
    try:
        cache_service.clear_all()
        return {"message": "Cache cleared successfully"}

    except Exception as e:
        logger.error(f"Failed to clear cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/quota/reset")
async def reset_quota():
    """
    クォータを手動リセット（テスト・デバッグ用）

    注意: 本番環境では使用を制限することを推奨
    """
    try:
        quota_manager.reset_quota()
        return {"message": "Quota reset successfully"}

    except Exception as e:
        logger.error(f"Failed to reset quota: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
