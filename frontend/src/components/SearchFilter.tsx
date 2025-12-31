import { useState } from 'react';
import { Search, Filter, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { Channel } from '@/types/channel';

interface SearchFilterProps {
  channels: Channel[];
  onFilteredChannelsChange: (channels: Channel[]) => void;
}

export function SearchFilter({ channels, onFilteredChannelsChange }: SearchFilterProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [minSubscribers, setMinSubscribers] = useState('');
  const [maxSubscribers, setMaxSubscribers] = useState('2000');
  const [minScore, setMinScore] = useState('');

  const applyFilters = () => {
    let filtered = [...channels];

    // テキスト検索
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(
        (ch) =>
          ch.snippet.title.toLowerCase().includes(term) ||
          ch.snippet.description.toLowerCase().includes(term)
      );
    }

    // 登録者数フィルター
    if (minSubscribers || maxSubscribers) {
      filtered = filtered.filter((ch) => {
        if (ch.statistics.hiddenSubscriberCount) return true;
        const count = parseInt(ch.statistics.subscriberCount || '0');
        const min = minSubscribers ? parseInt(minSubscribers) : 0;
        const max = maxSubscribers ? parseInt(maxSubscribers) : Infinity;
        return count >= min && count <= max;
      });
    }

    // スコアフィルター
    if (minScore) {
      const min = parseFloat(minScore);
      filtered = filtered.filter((ch) => (ch.activity_score || 0) >= min);
    }

    onFilteredChannelsChange(filtered);
  };

  const clearFilters = () => {
    setSearchTerm('');
    setMinSubscribers('');
    setMaxSubscribers('2000');
    setMinScore('');
    onFilteredChannelsChange(channels);
  };

  const hasActiveFilters = searchTerm || minSubscribers || minScore || maxSubscribers !== '2000';

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
          <Input
            type="text"
            placeholder="チャンネル名や説明文で検索..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && applyFilters()}
            className="pl-10"
          />
        </div>
        <Button onClick={applyFilters} className="bg-slate-900 hover:bg-slate-800">
          <Filter className="w-4 h-4 mr-2" />
          検索
        </Button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <label className="text-xs text-slate-600 dark:text-slate-400 mb-1 block">
            最小登録者数
          </label>
          <Input
            type="number"
            placeholder="0"
            value={minSubscribers}
            onChange={(e) => setMinSubscribers(e.target.value)}
            min="0"
          />
        </div>
        <div>
          <label className="text-xs text-slate-600 dark:text-slate-400 mb-1 block">
            最大登録者数
          </label>
          <Input
            type="number"
            placeholder="2000"
            value={maxSubscribers}
            onChange={(e) => setMaxSubscribers(e.target.value)}
            min="0"
          />
        </div>
        <div>
          <label className="text-xs text-slate-600 dark:text-slate-400 mb-1 block">
            最小スコア
          </label>
          <Input
            type="number"
            placeholder="0"
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
            min="0"
            max="100"
            step="0.1"
          />
        </div>
      </div>

      {hasActiveFilters && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-600 dark:text-slate-400">
            フィルター適用中:
          </span>
          <div className="flex flex-wrap gap-2">
            {searchTerm && (
              <Badge variant="secondary">
                検索: {searchTerm}
              </Badge>
            )}
            {minSubscribers && (
              <Badge variant="secondary">
                登録者 ≥ {minSubscribers}
              </Badge>
            )}
            {maxSubscribers !== '2000' && (
              <Badge variant="secondary">
                登録者 ≤ {maxSubscribers}
              </Badge>
            )}
            {minScore && (
              <Badge variant="secondary">
                スコア ≥ {minScore}
              </Badge>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={clearFilters}
              className="h-6 px-2"
            >
              <X className="w-3 h-3 mr-1" />
              クリア
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
