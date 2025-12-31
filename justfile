# YouTube Channel Finder - Justfile

# デフォルトレシピを表示
default:
    @just --list

# Backend

# バックエンドの依存関係をインストール
backend-install:
    cd backend && uv sync

# バックエンド開発サーバーを起動
backend-dev:
    cd backend && uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 --loop asyncio

# バックエンドテストを実行
backend-test:
    cd backend && uv run pytest -v

# Frontend

# フロントエンドの依存関係をインストール
frontend-install:
    cd frontend && pnpm install

# フロントエンド開発サーバーを起動
frontend-dev:
    cd frontend && pnpm run dev

# フロントエンドをビルド
frontend-build:
    cd frontend && pnpm run build

# フロントエンドのプレビュー
frontend-preview:
    cd frontend && pnpm run preview

# Docker

# Dockerコンテナを起動（Redis）
docker-up:
    docker compose up -d

# Dockerコンテナを停止
docker-down:
    docker compose down

# Dockerコンテナのログを表示
docker-logs:
    docker compose logs -f

# Full Stack

# 全体の開発環境を起動（Redis + Backend + Frontend）
dev: docker-up
    #!/usr/bin/env bash
    echo "Starting development environment..."
    echo "Redis: http://localhost:6379"
    echo "Backend API: http://localhost:8000"
    echo "Frontend: http://localhost:5173"
    echo ""
    echo "Press Ctrl+C to stop all services"
    trap 'docker compose down' EXIT
    cd backend && uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 --loop asyncio &
    cd frontend && pnpm run dev &
    wait

# 環境のクリーンアップ
clean:
    docker compose down -v
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type d -name "node_modules" -exec rm -rf {} +
    find . -type d -name ".pytest_cache" -exec rm -rf {} +

# .envファイルを作成（.env.exampleからコピー）
setup-env:
    @if [ ! -f backend/.env ]; then \
        cp backend/.env.example backend/.env; \
        echo ".env file created. Please edit backend/.env and add your YOUTUBE_API_KEY"; \
    else \
        echo ".env file already exists"; \
    fi
