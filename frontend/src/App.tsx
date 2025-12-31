import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2, AlertCircle, Youtube, TrendingUp } from 'lucide-react';
import { channelApi } from '@/services/api';
import { ChannelCard } from '@/components/ChannelCard';
import { SearchFilter } from '@/components/SearchFilter';
import { SearchControl } from '@/components/SearchControl';
import type { Channel } from '@/types/channel';
import { Badge } from '@/components/ui/badge';

function App() {
  const [filteredChannels, setFilteredChannels] = useState<Channel[]>([]);

  const { data, isLoading, error } = useQuery({
    queryKey: ['channels'],
    queryFn: () => channelApi.getDatabaseChannels(),
    staleTime: 1000 * 60 * 5, // 5分間キャッシュ
  });

  useEffect(() => {
    if (data?.channels) {
      setFilteredChannels(data.channels);
    }
  }, [data]);

  const sortByScore = () => {
    const sorted = [...filteredChannels].sort(
      (a, b) => (b.activity_score || 0) - (a.activity_score || 0)
    );
    setFilteredChannels(sorted);
  };

  const sortBySubscribers = () => {
    const sorted = [...filteredChannels].sort((a, b) => {
      const aCount = parseInt(a.statistics.subscriberCount || '0');
      const bCount = parseInt(b.statistics.subscriberCount || '0');
      return bCount - aCount;
    });
    setFilteredChannels(sorted);
  };

  const sortByDate = () => {
    const sorted = [...filteredChannels].sort(
      (a, b) =>
        new Date(b.snippet.publishedAt).getTime() -
        new Date(a.snippet.publishedAt).getTime()
    );
    setFilteredChannels(sorted);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-slate-600 mx-auto mb-4" />
          <p className="text-slate-600 dark:text-slate-400">
            チャンネルを検索中...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-50 mb-2">
            エラーが発生しました
          </h2>
          <p className="text-slate-600 dark:text-slate-400">
            {error instanceof Error ? error.message : 'チャンネルの取得に失敗しました'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* ヘッダー */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <Youtube className="w-10 h-10 text-red-600" />
            <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50">
              YouTube Channel Finder
            </h1>
          </div>
          <p className="text-slate-600 dark:text-slate-400">
            2024年以降に開始されたゲーム配信チャンネルを検索
          </p>
        </div>

        {/* データ収集コントロール */}
        <SearchControl />

        {/* クォータ情報 */}
        {data?.quota_status && (
          <div className="mb-6 p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
            <div className="flex flex-wrap gap-4 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-slate-600 dark:text-slate-400">
                  APIクォータ:
                </span>
                <Badge variant="outline">
                  {data.quota_status.used.toLocaleString()} /{' '}
                  {data.quota_status.limit.toLocaleString()} units
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-slate-600 dark:text-slate-400">
                  キャッシュヒット:
                </span>
                <Badge variant="secondary">
                  {data.cached_keywords} キーワード
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-slate-600 dark:text-slate-400">
                  検索結果:
                </span>
                <Badge variant="secondary">
                  {data.total_count} チャンネル
                </Badge>
              </div>
            </div>
          </div>
        )}

        {/* 検索・フィルター */}
        <div className="mb-6 p-6 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
          <SearchFilter
            channels={data?.channels || []}
            onFilteredChannelsChange={setFilteredChannels}
          />
        </div>

        {/* ソート */}
        <div className="mb-6 flex flex-wrap gap-2">
          <span className="text-sm text-slate-600 dark:text-slate-400 self-center">
            並び替え:
          </span>
          <button
            onClick={sortByScore}
            className="text-sm px-3 py-1 rounded-md bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-900 dark:text-slate-50 transition-colors"
          >
            <TrendingUp className="w-3 h-3 inline mr-1" />
            スコア順
          </button>
          <button
            onClick={sortBySubscribers}
            className="text-sm px-3 py-1 rounded-md bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-900 dark:text-slate-50 transition-colors"
          >
            登録者数順
          </button>
          <button
            onClick={sortByDate}
            className="text-sm px-3 py-1 rounded-md bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-900 dark:text-slate-50 transition-colors"
          >
            作成日順
          </button>
        </div>

        {/* チャンネル一覧 */}
        {filteredChannels.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-slate-600 dark:text-slate-400">
              検索条件に一致するチャンネルが見つかりませんでした
            </p>
          </div>
        ) : (
          <>
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
              {filteredChannels.length} 件のチャンネル
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredChannels.map((channel) => (
                <ChannelCard key={channel.id} channel={channel} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default App;
