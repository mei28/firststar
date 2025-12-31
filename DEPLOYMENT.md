# デプロイガイド

このガイドでは、YouTube Channel FinderをRender（バックエンド）とGitHub Pages（フロントエンド）にデプロイする方法を説明します。

## 前提条件

- GitHubアカウント
- Renderアカウント（https://render.com）
- YouTube Data API v3のAPIキー

## データ管理について

### 重複排除の仕組み

1. **検索時の重複排除**
   - 検索キーワードごとにチャンネルIDをsetで管理
   - 同じキーワードで再検索した場合、Redisキャッシュから取得（6時間有効）

2. **データベース永続化**
   - PostgreSQLに検索結果を保存
   - 既存チャンネルは更新、新規チャンネルは挿入
   - `search_keywords`フィールドで発見元キーワードを記録

3. **共有可能なデータ**
   - 複数ユーザーが同じデータベースにアクセス
   - みんなで検索結果を蓄積可能
   - 重複検索を避けてAPIクォータを節約

## バックエンドのデプロイ（Render）

### 1. GitHubリポジトリの作成

```bash
cd /Users/mei/Documents/firststar
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/youtube-channel-finder.git
git push -u origin main
```

### 2. Renderでデプロイ

1. [Render Dashboard](https://dashboard.render.com/)にログイン

2. **New > Blueprint**をクリック

3. GitHubリポジトリを接続

4. `render.yaml`を検出して自動設定

5. **環境変数を設定**:
   - `YOUTUBE_API_KEY`: YouTube APIキーを設定
   - `CORS_ORIGINS`: `https://YOUR_USERNAME.github.io` に変更
   - その他は自動設定される

6. **デプロイ**をクリック

7. デプロイ完了後、APIのURLをコピー:
   - 例: `https://youtube-channel-finder-api.onrender.com`

### 3. データベースの確認

Renderのダッシュボードから：
- PostgreSQL > `youtube-finder-db` を確認
- 接続情報は自動的に`DATABASE_URL`環境変数に設定される

## フロントエンドのデプロイ（GitHub Pages）

### 1. GitHub Pagesを有効化

1. GitHubリポジトリの **Settings** > **Pages**
2. **Source**: "GitHub Actions" を選択
3. 保存

### 2. GitHub Secretsを設定

1. リポジトリの **Settings** > **Secrets and variables** > **Actions**
2. **New repository secret**をクリック
3. 以下のSecretを追加:

```
Name: VITE_API_URL
Value: https://youtube-channel-finder-api.onrender.com
```

### 3. デプロイ

```bash
git add .
git commit -m "Add deployment configuration"
git push
```

GitHub Actionsが自動的にビルド・デプロイします。

### 4. 確認

- アクション完了後、`https://YOUR_USERNAME.github.io/youtube-channel-finder/` にアクセス
- フロントエンドが表示され、Render APIと通信できることを確認

## CORS設定の更新

フロントエンドのURLが確定したら、RenderのCORS設定を更新：

1. Render Dashboard > `youtube-channel-finder-api` > Environment
2. `CORS_ORIGINS`を更新:
   ```
   https://YOUR_USERNAME.github.io
   ```
3. デプロイを再実行

## データベースから検索結果を取得

### API経由

```bash
# すべての保存済みチャンネルを取得
curl https://youtube-channel-finder-api.onrender.com/api/channels/database

# スコア順でソート
curl "https://youtube-channel-finder-api.onrender.com/api/channels/database?order_by=activity_score%20DESC&limit=50"

# 登録者数順でソート
curl "https://youtube-channel-finder-api.onrender.com/api/channels/database?order_by=subscriber_count%20DESC&limit=50"
```

### フロントエンドの更新

フロントエンドで既存のデータベースから取得する場合、`App.tsx`を更新：

```typescript
// データベースから取得
const { data } = useQuery({
  queryKey: ['database-channels'],
  queryFn: () => axios.get('/api/channels/database?limit=100').then(res => res.data),
});
```

## データ管理のベストプラクティス

### 1. 定期的な検索

Render CronJobを設定して定期的に検索を実行：

```yaml
# render.yaml に追加
services:
  - type: cron
    name: daily-channel-search
    schedule: "0 0 * * *"  # 毎日0時
    runtime: python
    rootDir: backend
    buildCommand: "uv sync"
    startCommand: "uv run python scripts/daily_search.py"
```

### 2. データのバックアップ

Renderの無料プランでは自動バックアップがないため、定期的にエクスポート：

```bash
# PostgreSQLからエクスポート
pg_dump $DATABASE_URL > backup.sql
```

### 3. 古いデータのクリーンアップ

定期的に古いデータを削除するスクリプトを作成：

```sql
-- 6ヶ月以上更新されていないチャンネルを削除
DELETE FROM channels
WHERE last_updated_at < NOW() - INTERVAL '6 months';
```

## トラブルシューティング

### APIクォータ超過

- Renderの環境変数 `QUOTA_DAILY_LIMIT` を調整
- キャッシュを活用（`use_cache=true`）
- 検索頻度を減らす

### データベース接続エラー

- Renderのダッシュボードでデータベースの状態を確認
- `DATABASE_URL`環境変数が正しく設定されているか確認
- ログを確認: Render Dashboard > Logs

### CORS エラー

- `CORS_ORIGINS`にフロントエンドのURLが含まれているか確認
- プロトコル（http/https）が正しいか確認

## コスト

- **Render Free Plan**:
  - Web Service: 750時間/月（1サービスで十分）
  - PostgreSQL: 90日間無料、その後削除
  - Redis: 25MB無料

- **GitHub Pages**: 完全無料

- **YouTube Data API**: 1日10,000 units無料

## まとめ

この構成により：
- ✅ データの重複を避けて効率的に検索
- ✅ PostgreSQLでデータを永続化
- ✅ みんなで検索結果を共有可能
- ✅ 無料で運用可能
