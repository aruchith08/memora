import { useState, useEffect, useCallback } from 'react';
import { DashboardNav } from '../components/dashboard/DashboardNav';
import { SystemStatusCard } from '../components/dashboard/SystemStatusCard';
import { MemorySearchSection } from '../components/dashboard/MemorySearchSection';
import { ReasoningTraceCard } from '../components/dashboard/ReasoningTraceCard';
import { MemoryFeedSection } from '../components/dashboard/MemoryFeedSection';
import { api, ApiError } from '../services/api';
import { HealthResponse, MemoryItem, LatestReasoningResult } from '../types/api';

export default function DashboardPage() {
  // Global backend state
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'connecting' | 'disconnected'>('connecting');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [effectiveUid, setEffectiveUid] = useState<string | null>(null);
  const [isHealthLoading, setIsHealthLoading] = useState(true);

  // Memories feed state
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [memoryCount, setMemoryCount] = useState(0);
  const [memoryLimit, setMemoryLimit] = useState(20);
  const [isMemoriesLoading, setIsMemoriesLoading] = useState(true);
  const [memoriesError, setMemoriesError] = useState<string | null>(null);

  // Latest reasoning state
  const [reasoning, setReasoning] = useState<LatestReasoningResult | null>(null);
  const [isReasoningLoading, setIsReasoningLoading] = useState(true);
  const [reasoningError, setReasoningError] = useState<string | null>(null);

  // Global refresh state
  const [isRefreshing, setIsRefreshing] = useState(false);

  // 1. Fetch System Health
  const loadHealth = useCallback(async () => {
    setIsHealthLoading(true);
    try {
      const data = await api.getHealth();
      setHealth(data);
      setConnectionStatus('connected');
    } catch {
      setHealth(null);
      setConnectionStatus('disconnected');
    } finally {
      setIsHealthLoading(false);
    }
  }, []);

  // 2. Fetch Recent Memories
  const loadMemories = useCallback(async (currentLimit: number) => {
    setIsMemoriesLoading(true);
    setMemoriesError(null);
    try {
      const data = await api.getRecentMemories(currentLimit);
      setMemories(data.memories || []);
      setMemoryCount(data.count || 0);
      if (data.uid) {
        setEffectiveUid(data.uid);
      }
      setConnectionStatus('connected');
    } catch (err) {
      if (err instanceof ApiError) {
        setMemoriesError(err.detail || err.message);
      } else if (err instanceof Error) {
        setMemoriesError(err.message);
      } else {
        setMemoriesError('Unable to load memories.');
      }
      if (err instanceof ApiError && err.status === 0) {
        setConnectionStatus('disconnected');
      }
    } finally {
      setIsMemoriesLoading(false);
    }
  }, []);

  // 3. Fetch Latest Reasoning Run
  const loadReasoning = useCallback(async () => {
    setIsReasoningLoading(true);
    setReasoningError(null);
    try {
      const data = await api.getLatestReasoning();
      setReasoning(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setReasoningError(err.detail || err.message);
      } else if (err instanceof Error) {
        setReasoningError(err.message);
      } else {
        setReasoningError('Unable to load reasoning trace.');
      }
    } finally {
      setIsReasoningLoading(false);
    }
  }, []);

  // Refresh all dashboard data
  const handleRefreshAll = useCallback(async () => {
    setIsRefreshing(true);
    await Promise.allSettled([
      loadHealth(),
      loadMemories(memoryLimit),
      loadReasoning(),
    ]);
    setIsRefreshing(false);
  }, [loadHealth, loadMemories, loadReasoning, memoryLimit]);

  // Initial load
  useEffect(() => {
    handleRefreshAll();
  }, [handleRefreshAll]);

  // Handle memory limit changes
  const handleLimitChange = (newLimit: number) => {
    setMemoryLimit(newLimit);
    loadMemories(newLimit);
  };

  return (
    <div className="min-h-screen bg-canvas text-ink-primary flex flex-col">
      {/* Navigation Bar */}
      <DashboardNav
        connectionStatus={connectionStatus}
        onRefreshAll={handleRefreshAll}
        isRefreshing={isRefreshing}
      />

      {/* Main Content Dashboard */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-6">
        {/* System Health & Identity Banner */}
        <SystemStatusCard
          health={health}
          effectiveUid={effectiveUid}
          isLoading={isHealthLoading}
          isOffline={connectionStatus === 'disconnected'}
          onRetry={handleRefreshAll}
        />

        {/* Top Split Row: Semantic Search & Latest Reasoning */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          {/* Semantic Search Panel */}
          <MemorySearchSection />

          {/* Latest Recorded Reasoning Panel */}
          <ReasoningTraceCard
            reasoning={reasoning}
            isLoading={isReasoningLoading}
            error={reasoningError}
            onRefresh={loadReasoning}
          />
        </div>

        {/* Full-width Chronological Recent Memories Feed */}
        <MemoryFeedSection
          memories={memories}
          count={memoryCount}
          effectiveUid={effectiveUid}
          isLoading={isMemoriesLoading}
          error={memoriesError}
          limit={memoryLimit}
          onLimitChange={handleLimitChange}
          onRefresh={() => loadMemories(memoryLimit)}
        />
      </main>

      {/* Dashboard Footer */}
      <footer className="border-t border-surface-border py-4 bg-canvas text-center">
        <p className="text-[11px] text-ink-faint">
          MEMORA Console · Local vector storage with Lyzr multi-agent reasoning
        </p>
      </footer>
    </div>
  );
}
