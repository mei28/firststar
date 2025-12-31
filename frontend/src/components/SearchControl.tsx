import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Search, Loader2, Database, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { channelApi } from '@/services/api';
import { Badge } from '@/components/ui/badge';

export function SearchControl() {
  const [maxResults, setMaxResults] = useState(10);
  const queryClient = useQueryClient();

  // クォータ状況を取得
  const { data: quotaData, refetch: refetchQuota } = useQuery({
    queryKey: ['quota'],
    queryFn: () => channelApi.getQuotaStatus(),
    refetchInterval: 10000, // 10秒ごとに更新
  });

  // チャンネル検索を実行
  const searchMutation = useMutation({
    mutationFn: (maxResultsPerKeyword: number) =>
      channelApi.searchChannels({ max_results_per_keyword: maxResultsPerKeyword, use_cache: false }),
    onSuccess: () => {
      // 検索完了後、チャンネルリストとクォータを更新
      queryClient.invalidateQueries({ queryKey: ['channels'] });
      refetchQuota();
    },
  });

  const handleSearch = () => {
    if (confirm(`${maxResults}件/キーワードで検索を実行しますか?\n\n※ APIクォータを消費します（約900 units）`)) {
      searchMutation.mutate(maxResults);
    }
  };

  const quotaUsed = quotaData?.quota_used || 0;
  const quotaLimit = quotaData?.quota_limit || 10000;
  const quotaRemaining = quotaLimit - quotaUsed;
  const quotaPercentage = (quotaUsed / quotaLimit) * 100;

  return (
    <Card className="mb-6 border-slate-300">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5" />
          データ収集コントロール
        </CardTitle>
        <CardDescription>
          YouTube APIでチャンネルを検索してデータベースに保存します
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* クォータ使用状況 */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-600">APIクォータ使用状況</span>
            <span className="font-mono font-semibold">
              {quotaUsed.toLocaleString()} / {quotaLimit.toLocaleString()} units
            </span>
          </div>
          <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all ${
                quotaPercentage > 80
                  ? 'bg-red-500'
                  : quotaPercentage > 50
                  ? 'bg-amber-500'
                  : 'bg-emerald-500'
              }`}
              style={{ width: `${quotaPercentage}%` }}
            />
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span>残り: {quotaRemaining.toLocaleString()} units</span>
            {quotaData?.reset_at && (
              <span>• リセット: {new Date(quotaData.reset_at).toLocaleString('ja-JP')}</span>
            )}
          </div>
        </div>

        {/* 検索パラメータ */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700">
            キーワードあたりの取得件数
          </label>
          <div className="flex gap-2 items-center">
            <Input
              type="number"
              min="5"
              max="50"
              value={maxResults}
              onChange={(e) => setMaxResults(Number(e.target.value))}
              className="w-24"
            />
            <span className="text-sm text-slate-600">件/キーワード</span>
            <Badge variant="outline" className="ml-auto">
              約900 units消費
            </Badge>
          </div>
          <p className="text-xs text-slate-500">
            デフォルトキーワード9種類 × {maxResults}件ずつ検索します
          </p>
        </div>

        {/* 実行ボタン */}
        <div className="flex gap-2">
          <Button
            onClick={handleSearch}
            disabled={searchMutation.isPending || quotaRemaining < 900}
            className="flex-1"
          >
            {searchMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                検索実行中...
              </>
            ) : (
              <>
                <Search className="mr-2 h-4 w-4" />
                チャンネル検索を実行
              </>
            )}
          </Button>
          <Button
            variant="outline"
            onClick={() => refetchQuota()}
            disabled={searchMutation.isPending}
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>

        {quotaRemaining < 900 && (
          <div className="text-sm text-amber-600 bg-amber-50 p-3 rounded border border-amber-200">
            ⚠️ クォータ不足: 明日のリセット後に実行してください
          </div>
        )}

        {searchMutation.isSuccess && (
          <div className="text-sm text-emerald-600 bg-emerald-50 p-3 rounded border border-emerald-200">
            ✓ 検索完了！ {searchMutation.data.total_count}件のチャンネルを発見しました
          </div>
        )}

        {searchMutation.isError && (
          <div className="text-sm text-red-600 bg-red-50 p-3 rounded border border-red-200">
            ✗ エラー: {(searchMutation.error as Error).message}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
