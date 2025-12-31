import axios from 'axios';
import type { SearchResponse } from '@/types/channel';

// 本番環境ではRender APIのURL、開発環境ではプロキシ経由
const API_BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
});

export interface SearchParams {
  keywords?: string[];
  published_after?: string;
  max_results_per_keyword?: number;
  use_cache?: boolean;
}

export const channelApi = {
  searchChannels: async (params?: SearchParams): Promise<SearchResponse> => {
    const response = await api.get<SearchResponse>('/channels/search', {
      params: {
        keywords: params?.keywords,
        published_after: params?.published_after || '2024-01-01T00:00:00Z',
        max_results_per_keyword: params?.max_results_per_keyword || 20,
        use_cache: params?.use_cache !== false,
      },
    });
    return response.data;
  },

  getDatabaseChannels: async (): Promise<SearchResponse> => {
    const response = await api.get<SearchResponse>('/channels/database', {
      params: {
        limit: 100,
        order_by: 'activity_score DESC',
      },
    });
    return response.data;
  },

  getQuotaStatus: async () => {
    const response = await api.get('/quota/status');
    return response.data;
  },
};
