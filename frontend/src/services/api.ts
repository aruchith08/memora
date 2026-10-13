import {
  HealthResponse,
  MemoryListResponse,
  MemorySearchResponse,
  LatestReasoningResult,
} from '../types/api';

export class ApiError extends Error {
  public status: number;
  public detail?: string;

  constructor(status: number, message: string, detail?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

const DEFAULT_TIMEOUT_MS = 10000;
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '');

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const targetUrl = endpoint.startsWith('http://') || endpoint.startsWith('https://')
    ? endpoint
    : `${API_BASE_URL}${cleanEndpoint}`;

  try {
    const response = await fetch(targetUrl, {
      ...options,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });

    clearTimeout(timeoutId);

    let data: unknown;
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      try {
        data = await response.json();
      } catch {
        throw new ApiError(response.status, 'Invalid JSON returned by server.');
      }
    } else {
      const text = await response.text();
      data = { message: text };
    }

    if (!response.ok) {
      let detailMsg = 'Request failed';
      if (data && typeof data === 'object') {
        const d = data as Record<string, unknown>;
        if (typeof d.detail === 'string') {
          detailMsg = d.detail;
        } else if (typeof d.message === 'string') {
          detailMsg = d.message;
        }
      }
      throw new ApiError(response.status, detailMsg, typeof data === 'object' ? JSON.stringify(data) : undefined);
    }

    return data as T;
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    if (err instanceof ApiError) {
      throw err;
    }
    if (err instanceof Error) {
      if (err.name === 'AbortError') {
        throw new ApiError(0, 'Request timed out after 10s. Backend may be overloaded or unreachable.');
      }
      throw new ApiError(0, err.message || 'Network connection error. Backend may be offline.');
    }
    throw new ApiError(0, 'An unknown error occurred while communicating with the backend.');
  }
}

export const api = {
  getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>('/health');
  },

  getRecentMemories(limit: number = 20): Promise<MemoryListResponse> {
    const safeLimit = Math.max(1, Math.min(50, limit));
    return request<MemoryListResponse>(`/memories?limit=${safeLimit}`);
  },

  searchMemories(query: string, limit: number = 5): Promise<MemorySearchResponse> {
    const safeLimit = Math.max(1, Math.min(50, limit));
    return request<MemorySearchResponse>('/memories/search', {
      method: 'POST',
      body: JSON.stringify({ query: query.trim(), limit: safeLimit }),
    });
  },

  getLatestReasoning(): Promise<LatestReasoningResult | null> {
    return request<LatestReasoningResult>('/reason/latest').catch((err) => {
      if (err instanceof ApiError && err.status === 404) {
        return null;
      }
      throw err;
    });
  },
};
