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

  // Handle memory deletion
  const handleDeleteMemory = async (id: string) => {
    try {
      await api.deleteMemory(id);
      // Remove locally from UI state immediately
      setMemories((prev) => prev.filter((m) => m.id !== id));
      setMemoryCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      const msg = err instanceof ApiError ? (err.detail || err.message) : 'Failed to forget memory';
      alert(`Could not delete memory: ${msg}`);
    }
  };

  return (
    <div className="min-h-screen bg-[#FBFBFA] text-slate-900 flex flex-col font-sans">
      {/* Navigation Bar */}
      <DashboardNav
        connectionStatus={connectionStatus}
        onRefreshAll={handleRefreshAll}
        isRefreshing={isRefreshing}
      />

      {/* Main Content Dashboard */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-6">
        {/* 1. Hero Search Section */}
        <MemorySearchSection />

        {/* 2. Runtime Environment (3 Horizontal Cards) */}
        <SystemStatusCard
          health={health}
          effectiveUid={effectiveUid}
          isLoading={isHealthLoading}
          isOffline={connectionStatus === 'disconnected'}
          onRetry={handleRefreshAll}
        />

        {/* 3. Main Split Row: Left = Recent Voice Memories (8 cols), Right = Latest Reasoning (4 cols) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left: Chronological Recent Memories Feed */}
          <div className="lg:col-span-8">
            <MemoryFeedSection
              memories={memories}
              count={memoryCount}
              effectiveUid={effectiveUid}
              isLoading={isMemoriesLoading}
              error={memoriesError}
              limit={memoryLimit}
              onLimitChange={handleLimitChange}
              onRefresh={() => loadMemories(memoryLimit)}
              onDeleteMemory={handleDeleteMemory}
            />
          </div>

          {/* Right: Latest Recorded Reasoning Panel */}
          <div className="lg:col-span-4">
            <ReasoningTraceCard
              reasoning={reasoning}
              isLoading={isReasoningLoading}
              error={reasoningError}
              onRefresh={loadReasoning}
              onRunTestQuery={() => {
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
            />
          </div>
        </div>
      </main>

      {/* Dashboard Footer */}
      <footer className="border-t border-slate-200/80 py-4 bg-white text-center">
        <p className="text-[11px] text-slate-400">
          MEMORA Console &middot; Qdrant Cloud Vector Storage with Lyzr Multi-Agent Reasoning
        </p>
      </footer>
    </div>
  );
}
