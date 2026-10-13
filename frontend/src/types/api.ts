export interface HealthResponse {
  status: string;
  app: string;
  qdrant_mode: string;
  collection: string;
}

export interface MemoryItem {
  id: string;
  text: string;
  created_at: string;
  source: string;
  metadata?: Record<string, unknown> | null;
}

export interface MemoryListResponse {
  status: string;
  count: number;
  uid?: string | null;
  memories: MemoryItem[];
}

export interface MemorySearchResult {
  id: string;
  score: number;
  text: string;
  payload: {
    uid?: string;
    text?: string;
    source?: string;
    created_at?: string;
    ts?: number;
    [key: string]: unknown;
  };
}

export interface MemorySearchResponse {
  status: string;
  query: string;
  results: MemorySearchResult[];
}

export interface LatestReasoningResult {
  status?: string;
  message?: string;
  uid?: string;
  session_id?: string | null;
  question?: string;
  detected_as_query?: boolean;
  manager_agent_id?: string | null;
  orchestration_mode?: string;
  delegation_observed?: boolean;
  telemetry_status?: string;
  workers_invoked?: Array<string | { agent_id?: string; agent_name?: string; status?: string }>;
  execution_trace?: Array<{
    agent?: string;
    action?: string;
    target?: string;
    [key: string]: unknown;
  }>;
  retrieved_memory_count?: number;
  retrieved_memory_ids?: string[];
  manager_answer?: string | null;
  lyzr_answer?: string | null;
  notification_status?: string;
  notification_error?: string | null;
  notification_status_code?: number | null;
  processing_status?: string;
  event_status?: string;
  timestamp?: string;
  error?: string | null;
}
