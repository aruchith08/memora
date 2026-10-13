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
      <div className="p-4 sm:p-5 rounded-2xl border border-rose-200 bg-rose-50/70 text-slate-900 shadow-2xs">
        <div className="flex items-start gap-3">
          <AlertTriangle size={18} className="text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-rose-900">Backend Service Offline</h3>
            <p className="mt-1 text-xs text-rose-800 leading-relaxed">
              Unable to reach the MEMORA FastAPI service. Check network connectivity or verify backend deployment health.
            </p>
            <button
              onClick={onRetry}
              className="mt-3 inline-flex items-center px-3 py-1.5 rounded-lg bg-rose-700 text-white text-xs font-medium hover:bg-rose-800 transition-colors shadow-2xs"
            >
              Retry Connection
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* 1. Vector Store Card */}
      <div className="p-4 rounded-2xl border border-slate-200/90 bg-white shadow-2xs">
        <div className="flex items-start gap-3.5 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-600 border border-purple-100 flex items-center justify-center shrink-0">
            <Database size={19} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-900">Vector Store</span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/60">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Connected
              </span>
            </div>
            <p
              className="text-xs text-slate-500 font-mono truncate mt-0.5"
              title={health?.qdrant_mode || 'Checking...'}
            >
              {isLoading ? 'Checking...' : health?.qdrant_mode || 'server (Qdrant Cloud)'}
            </p>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Collection: <span className="font-medium text-slate-600">{health?.collection || 'voice_memory'}</span>
            </p>
          </div>
        </div>
      </div>

      {/* 2. Identity Scope Card */}
      <div className="p-4 rounded-2xl border border-slate-200/90 bg-white shadow-2xs">
        <div className="flex items-start gap-3.5 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 border border-blue-100 flex items-center justify-center shrink-0">
            <Shield size={19} />
          </div>
          <div className="min-w-0 flex-1">
            <span className="text-sm font-semibold text-slate-900">Identity Scope</span>
            <p
              className="text-xs font-bold text-slate-800 font-mono truncate mt-0.5"
              title={effectiveUid || 'memora_demo_user'}
            >
              {isLoading ? 'Resolving...' : effectiveUid || 'memora_demo_user'}
            </p>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Demo partition (non-production boundary)
            </p>
          </div>
        </div>
      </div>

      {/* 3. Backend App Card */}
      <div className="p-4 rounded-2xl border border-slate-200/90 bg-white shadow-2xs">
        <div className="flex items-start gap-3.5 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100 flex items-center justify-center shrink-0">
            <Server size={19} />
          </div>
          <div className="min-w-0 flex-1">
            <span className="text-sm font-semibold text-slate-900">Backend App</span>
            <p className="text-xs font-bold text-slate-800 truncate mt-0.5">
              {health?.app || 'MEMORA Backend'}
            </p>
            <div className="flex items-center gap-1.5 mt-1">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/60">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                Healthy
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
