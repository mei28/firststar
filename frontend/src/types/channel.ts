export interface ChannelThumbnail {
  url: string;
  width: number;
  height: number;
}

export interface ChannelSnippet {
  title: string;
  description: string;
  customUrl?: string;
  publishedAt: string;
  thumbnails: {
    default: ChannelThumbnail;
    medium: ChannelThumbnail;
    high: ChannelThumbnail;
  };
  country?: string;
}

export interface ChannelStatistics {
  viewCount: string;
  subscriberCount?: string;
  hiddenSubscriberCount: boolean;
  videoCount: string;
}

export interface ChannelContentDetails {
  relatedPlaylists: {
    likes: string;
    uploads: string;
  };
}

export interface Channel {
  kind: string;
  etag: string;
  id: string;
  snippet: ChannelSnippet;
  contentDetails: ChannelContentDetails;
  statistics: ChannelStatistics;
  activity_score?: number;
}

export interface SearchResponse {
  channels: Channel[];
  total_count: number;
  quota_used: number;
  cached_keywords: number;
  quota_status: {
    used: number;
    remaining: number;
    limit: number;
    warning_threshold: number;
    is_exceeded: boolean;
    is_warning: boolean;
    reset_at: string | null;
  };
}
