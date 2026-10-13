import React from 'react';
import { Database, Shield, Server, AlertTriangle } from 'lucide-react';
import { HealthResponse } from '../../types/api';

interface SystemStatusCardProps {
  health: HealthResponse | null;
  effectiveUid: string | null;
  isLoading: boolean;
  isOffline: boolean;
  onRetry: () => void;
}

export const SystemStatusCard: React.FC<SystemStatusCardProps> = ({
  health,
  effectiveUid,
  isLoading,
  isOffline,
  onRetry,
}) => {
  if (isOffline) {
    return (
      <div className="p-4 sm:p-5 rounded-xl border border-rose-200 bg-rose-50/70 text-ink-primary shadow-sm">
        <div className="flex items-start gap-3">
          <AlertTriangle size={18} className="text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-rose-900">Backend Service Offline</h3>
            <p className="mt-1 text-xs text-rose-800 leading-relaxed">
              Cannot connect to the FastAPI backend at <code className="bg-rose-100 px-1 py-0.5 rounded font-mono text-[11px]">http://127.0.0.1:8000</code>.
              Ensure the Python backend is running via <code className="bg-rose-100 px-1 py-0.5 rounded font-mono text-[11px]">uvicorn app:app --port 8000</code>.
            </p>
            <button
              onClick={onRetry}
              className="mt-3 inline-flex items-center px-3 py-1.5 rounded-md bg-rose-700 text-white text-xs font-medium hover:bg-rose-800 transition-colors shadow-xs"
            >
              Retry Connection
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-5 rounded-xl border border-surface-border bg-white shadow-card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xs font-semibold text-ink-muted uppercase tracking-wider flex items-center gap-1.5">
          <Server size={14} className="text-accent-blue" />
          Runtime Environment
        </h2>
        {isLoading && (
          <span className="text-[11px] text-ink-muted animate-pulse">Checking status...</span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Qdrant Mode */}
        <div className="p-3 rounded-lg border border-surface-border bg-surface-muted/30">
          <div className="flex items-center gap-2 mb-1">
            <Database size={14} className="text-ink-secondary" />
            <span className="text-xs font-medium text-ink-secondary">Vector Store</span>
          </div>
          <p className="text-xs font-mono font-medium text-ink-primary truncate" title={health?.qdrant_mode || 'Checking...'}>
            {isLoading ? 'Loading...' : health?.qdrant_mode || 'Unavailable'}
          </p>
          <p className="mt-1 text-[10px] text-ink-muted">
            Collection: <span className="font-mono text-ink-secondary">{health?.collection || 'voice_memory'}</span>
          </p>
        </div>

        {/* Demo Identity Scoping */}
        <div className="p-3 rounded-lg border border-surface-border bg-surface-muted/30">
          <div className="flex items-center gap-2 mb-1">
            <Shield size={14} className="text-ink-secondary" />
            <span className="text-xs font-medium text-ink-secondary">Identity Scope</span>
          </div>
          <p className="text-xs font-mono font-medium text-ink-primary truncate" title={effectiveUid || 'default_user'}>
            {isLoading ? 'Resolving...' : effectiveUid || 'default_user'}
          </p>
          <p className="mt-1 text-[10px] text-ink-muted">
            Demo partition (non-production boundary)
          </p>
        </div>

        {/* Service Architecture */}
        <div className="p-3 rounded-lg border border-surface-border bg-surface-muted/30">
          <div className="flex items-center gap-2 mb-1">
            <Server size={14} className="text-ink-secondary" />
            <span className="text-xs font-medium text-ink-secondary">Backend App</span>
          </div>
          <p className="text-xs font-medium text-ink-primary truncate">
            {health?.app || 'MEMORA Backend'}
          </p>
          <p className="mt-1 text-[10px] text-ink-muted">
            Status: <span className="text-emerald-700 font-medium">Healthy</span>
          </p>
        </div>
      </div>
    </div>
  );
};
