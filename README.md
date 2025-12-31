# YouTube Channel Finder

友人のゲーム配信チャンネルを検索するWebアプリケーション

## 概要

2024年以降に開始された日本のゲーム配信チャンネル（登録者数2000人未満）を効率的に検索・特定するためのツールです。

### 主な機能

- YouTube Data API v3を使用した効率的なチャンネル検索
- 登録者数・チャンネル作成日・ゲーム関連度によるフィルタリング
- Redisキャッシュによるクォータ節約
- APIクォータ使用状況のリアルタイム監視

## 技術スタック

### バックエンド
- Python 3.11+
- FastAPI
- YouTube Data API v3
- Redis (キャッシュ)
- Pydantic (バリデーション)

### フロントエンド（今後実装）
- TypeScript
- React 18
- Vite
- Tailwind CSS

### インフラ
- Docker Compose
- just (タスクランナー)

## セットアップ

### 前提条件

- Python 3.11以上
- uv ([インストール方法](https://docs.astral.sh/uv/))
- Docker & Docker Compose
- just ([インストール方法](https://github.com/casey/just))
- YouTube Data API v3のAPIキー（[取得方法](#youtube-api-キーの取得)）

### 1. YouTube API キーの取得

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成
3. 「APIとサービス」→「ライブラリ」から「YouTube Data API v3」を有効化
4. 「APIとサービス」→「認証情報」から「APIキー」を作成
5. 作成したAPIキーをコピー

### 2. 環境変数の設定

```bash
# .envファイルを作成
just setup-env

# backend/.envを編集してAPIキーを設定
vim backend/.env
```

`backend/.env`:
```bash
YOUTUBE_API_KEY=YOUR_API_KEY_HERE  # ここにAPIキーを設定
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
QUOTA_DAILY_LIMIT=10000
QUOTA_WARNING_THRESHOLD=2000
API_HOST=0.0.0.0
API_PORT=8000
```

### 3. バックエンドのセットアップ

```bash
# uv で依存関係をインストール
just backend-install

# Redisコンテナを起動
just docker-up
```

### 4. 開発サーバーの起動

```bash
# バックエンドのみ起動
just backend-dev

# または全体（Redis + Backend）を起動
just dev
```

## 使用方法

### APIエンドポイント

バックエンドサーバー起動後、以下のエンドポイントが利用可能です:

#### 1. チャンネル検索
```bash
GET http://localhost:8000/api/channels/search

# パラメータ:
# - keywords: 検索キーワード（配列、オプション）
# - published_after: チャンネル作成日以降（デフォルト: 2024-01-01T00:00:00Z）
# - max_results_per_keyword: キーワードあたりの最大取得件数（デフォルト: 50）
# - use_cache: キャッシュ使用の有無（デフォルト: true）

# 例:
curl "http://localhost:8000/api/channels/search?keywords=ゲーム実況&keywords=APEX&max_results_per_keyword=50"
```

#### 2. クォータ状況確認
```bash
GET http://localhost:8000/api/quota/status

# 例:
curl http://localhost:8000/api/quota/status
```

#### 3. 特定チャンネル取得
```bash
GET http://localhost:8000/api/channels/{channel_id}

# 例:
curl http://localhost:8000/api/channels/UC_x5XG1OV2P6uZZ5FSM9Ttw
```

#### 4. キャッシュクリア（デバッグ用）
```bash
POST http://localhost:8000/api/cache/clear

# 例:
curl -X POST http://localhost:8000/api/cache/clear
```

### APIドキュメント

FastAPIの自動生成ドキュメント:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## プロジェクト構造

```
firststar/
├── backend/                      # Pythonバックエンド
│   ├── src/
│   │   ├── api/
│   │   │   ├── youtube_client.py    # YouTube Data API v3クライアント
│   │   │   └── quota_manager.py     # APIクォータ管理
│   │   ├── services/
│   │   │   ├── channel_search.py   # チャンネル検索オーケストレーター
│   │   │   ├── channel_filter.py   # フィルタリングロジック
│   │   │   └── cache_service.py    # Redisキャッシュ管理
│   │   ├── models/
│   │   │   └── channel.py          # チャンネルデータモデル
│   │   ├── config/
│   │   │   └── settings.py         # 環境変数・設定
│   │   └── main.py                 # FastAPIエントリーポイント
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                     # フロントエンド（今後実装）
│   └── src/
│
├── docker-compose.yml            # Redis環境
├── justfile                      # タスクランナー
└── README.md
```

## YouTube Data API クォータ戦略

### クォータコスト
- `search.list`: 100 units/call（高コスト）
- `channels.list`: 1 unit/call（低コスト）
- 1日上限: 10,000 units（約100回の検索）

### 節約テクニック
1. **重複排除**: 同一チャンネルの重複検索を防止
2. **バッチ取得**: channels.listは50件まとめて1 unit
3. **キャッシュ**: チャンネル情報24時間、検索結果6時間
4. **ページネーション制御**: 必要最小限のページ数に制限

## トラブルシューティング

### Redisに接続できない
```bash
# Redisコンテナの状態確認
docker ps | grep redis

# Redisコンテナを再起動
just docker-down
just docker-up
```

### APIクォータを超過した
```bash
# クォータ状況を確認
curl http://localhost:8000/api/quota/status

# クォータは翌日0時(UTC)に自動リセットされます
# テスト目的で手動リセットする場合:
curl -X POST http://localhost:8000/api/quota/reset
```

### キャッシュをクリアしたい
```bash
curl -X POST http://localhost:8000/api/cache/clear
```

## Justfileコマンド一覧

```bash
just --list                # 利用可能なコマンド一覧
just backend-install       # バックエンド依存関係インストール
just backend-dev           # バックエンド開発サーバー起動
just docker-up             # Redisコンテナ起動
just docker-down           # Dockerコンテナ停止
just docker-logs           # Dockerログ表示
just dev                   # 全体の開発環境起動
just clean                 # 環境のクリーンアップ
just setup-env             # .envファイル作成
```

## データ管理

### 重複排除の仕組み

1. **Redisキャッシュ**: 検索結果を6時間、チャンネル情報を24時間キャッシュ
2. **PostgreSQL永続化**: 検索したチャンネルをデータベースに保存
3. **重複チェック**: 既存チャンネルは更新、新規チャンネルのみ挿入

### データベース統計

```bash
# データベースの統計情報を確認
curl http://localhost:8000/api/quota/status

# 保存済みチャンネルを取得
curl http://localhost:8000/api/channels/database?limit=100
```

## デプロイ

本番環境へのデプロイ方法は [DEPLOYMENT.md](./DEPLOYMENT.md) を参照してください。

- **フロントエンド**: GitHub Pages（無料）
- **バックエンド**: Render（無料プランあり）
- **データベース**: Render PostgreSQL（90日間無料）

## ライセンス

MIT License

## 注意事項

- YouTube Data API v3の利用規約を遵守してください
- APIクォータ制限（1日10,000 units）に注意してください
- PostgreSQLを設定することで、複数ユーザーでデータを共有できます
