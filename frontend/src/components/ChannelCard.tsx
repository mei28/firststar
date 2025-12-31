import { ExternalLink, Users, Video, Calendar, TrendingUp } from 'lucide-react';
import type { Channel } from '@/types/channel';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface ChannelCardProps {
  channel: Channel;
}

export function ChannelCard({ channel }: ChannelCardProps) {
  const { snippet, statistics, activity_score } = channel;
  const channelUrl = `https://www.youtube.com/channel/${channel.id}`;

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ja-JP', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const formatNumber = (num: string | undefined) => {
    if (!num) return '不明';
    return parseInt(num).toLocaleString('ja-JP');
  };

  const getScoreColor = (score?: number) => {
    if (!score) return 'bg-slate-100 text-slate-900';
    if (score >= 80) return 'bg-emerald-100 text-emerald-900 dark:bg-emerald-900 dark:text-emerald-100';
    if (score >= 60) return 'bg-blue-100 text-blue-900 dark:bg-blue-900 dark:text-blue-100';
    if (score >= 40) return 'bg-amber-100 text-amber-900 dark:bg-amber-900 dark:text-amber-100';
    return 'bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-slate-100';
  };

  return (
    <Card className="hover:shadow-lg transition-shadow duration-300 overflow-hidden">
      <CardHeader className="pb-4">
        <div className="flex items-start gap-4">
          <img
            src={snippet.thumbnails.medium.url}
            alt={snippet.title}
            className="w-20 h-20 rounded-full object-cover border-2 border-slate-200 dark:border-slate-700"
          />
          <div className="flex-1 min-w-0">
            <CardTitle className="text-lg line-clamp-2 mb-2">
              {snippet.title}
            </CardTitle>
            <div className="flex flex-wrap gap-2">
              {activity_score !== undefined && (
                <Badge
                  variant="secondary"
                  className={getScoreColor(activity_score)}
                >
                  <TrendingUp className="w-3 h-3 mr-1" />
                  スコア: {activity_score.toFixed(1)}
                </Badge>
              )}
              {snippet.country && (
                <Badge variant="outline">
                  {snippet.country}
                </Badge>
              )}
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        <CardDescription className="line-clamp-3 text-sm">
          {snippet.description || 'チャンネルの説明はありません'}
        </CardDescription>

        <div className="grid grid-cols-2 gap-3 pt-2">
          <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
            <Users className="w-4 h-4" />
            <span>
              {statistics.hiddenSubscriberCount
                ? '非公開'
                : `${formatNumber(statistics.subscriberCount)}人`}
            </span>
          </div>

          <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
            <Video className="w-4 h-4" />
            <span>{formatNumber(statistics.videoCount)}本</span>
          </div>

          <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400 col-span-2">
            <Calendar className="w-4 h-4" />
            <span>{formatDate(snippet.publishedAt)}</span>
          </div>
        </div>
      </CardContent>

      <CardFooter>
        <Button
          variant="default"
          className="w-full bg-slate-900 hover:bg-slate-800 dark:bg-slate-50 dark:hover:bg-slate-200"
          onClick={() => window.open(channelUrl, '_blank')}
        >
          <ExternalLink className="w-4 h-4 mr-2" />
          チャンネルを開く
        </Button>
      </CardFooter>
    </Card>
  );
}
