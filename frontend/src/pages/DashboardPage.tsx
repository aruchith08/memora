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

  // Global refresh and protected deletion state
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isDeleteAuthOpen, setIsDeleteAuthOpen] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteAuthError, setDeleteAuthError] = useState<string | null>(null);
  const [isDeleteAuthLoading, setIsDeleteAuthLoading] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

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

  const deleteMemoryWithSession = async (id: string, accessToken: string) => {
    try {
      await api.deleteMemory(id, accessToken);
      setMemories((prev) => prev.filter((memory) => memory.id !== id));
      setMemoryCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        sessionStorage.removeItem('memora_dashboard_session');
        setPendingDeleteId(id);
        setDeleteAuthError('Your dashboard session expired. Enter the password again.');
        setIsDeleteAuthOpen(true);
        return;
      }
      const msg = err instanceof ApiError ? (err.detail || err.message) : 'Failed to forget memory';
      alert(`Could not delete memory: ${msg}`);
    }
  };

  // Ask for dashboard authorization before attempting a protected delete.
  const handleDeleteMemory = async (id: string) => {
    const accessToken = sessionStorage.getItem('memora_dashboard_session');
    if (!accessToken) {
      setPendingDeleteId(id);
      setDeleteAuthError(null);
      setIsDeleteAuthOpen(true);
      return;
    }
    await deleteMemoryWithSession(id, accessToken);
  };

  const handleDashboardLogin = async () => {
    setIsDeleteAuthLoading(true);
    setDeleteAuthError(null);
    try {
      const session = await api.createDashboardSession(deletePassword);
      sessionStorage.setItem('memora_dashboard_session', session.access_token);
      const idToDelete = pendingDeleteId;
      setDeletePassword('');
      setPendingDeleteId(null);
      setIsDeleteAuthOpen(false);
      if (idToDelete) {
        await deleteMemoryWithSession(idToDelete, session.access_token);
      }
    } catch (err) {
      const message = err instanceof ApiError ? (err.detail || err.message) : 'Dashboard login failed.';
      setDeleteAuthError(message);
    } finally {
      setIsDeleteAuthLoading(false);
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

      {isDeleteAuthOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 px-4" role="presentation">
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-auth-title"
            className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl"
          >
            <h2 id="delete-auth-title" className="text-lg font-semibold text-slate-900">Authorize memory deletion</h2>
            <p className="mt-2 text-sm text-slate-600">Enter the dashboard password to create a one-hour delete session.</p>
            <form
              className="mt-5 space-y-4"
              onSubmit={(event) => {
                event.preventDefault();
                void handleDashboardLogin();
              }}
            >
              <label htmlFor="dashboard-delete-password" className="block text-sm font-medium text-slate-700">
                Dashboard password
              </label>
              <input
                id="dashboard-delete-password"
                type="password"
                autoComplete="current-password"
                required
                value={deletePassword}
                onChange={(event) => setDeletePassword(event.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
              {deleteAuthError && <p role="alert" className="text-sm text-rose-600">{deleteAuthError}</p>}
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setIsDeleteAuthOpen(false);
                    setDeletePassword('');
                    setDeleteAuthError(null);
                    setPendingDeleteId(null);
                  }}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isDeleteAuthLoading || !deletePassword}
                  className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isDeleteAuthLoading ? 'Authorizing…' : 'Continue'}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
