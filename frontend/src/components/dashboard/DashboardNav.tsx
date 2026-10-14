import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, RefreshCw, Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';

interface DashboardNavProps {
  connectionStatus: 'connected' | 'connecting' | 'disconnected';
  onRefreshAll: () => void;
  isRefreshing: boolean;
}

export const DashboardNav: React.FC<DashboardNavProps> = ({
  connectionStatus,
  onRefreshAll,
  isRefreshing,
}) => {
  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-sm border-b border-slate-200/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Left: Brand & Console breadcrumb */}
        <div className="flex items-center gap-2.5">
          <Link
            to="/"
            className="text-slate-900 font-bold text-xl tracking-tight hover:opacity-85 transition-opacity"
          >
            Memora
          </Link>
          <span className="text-slate-300 font-light text-sm">/</span>
          <span className="text-xs font-semibold text-slate-700 bg-slate-100/90 px-2.5 py-0.5 rounded-full border border-slate-200">
            Console
          </span>
        </div>

        {/* Right: Status badge, refresh button & marketing site link */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Connection status badge */}
          <div
            className={cn(
              'inline-flex items-center gap-1.5 px-2 sm:px-3 py-1 rounded-full text-xs font-medium border transition-colors',
              connectionStatus === 'connected' &&
                'bg-emerald-50 text-emerald-700 border-emerald-200/80',
              connectionStatus === 'connecting' &&
                'bg-amber-50 text-amber-700 border-amber-200/80',
              connectionStatus === 'disconnected' &&
                'bg-rose-50 text-rose-700 border-rose-200/80'
            )}
            title={
              connectionStatus === 'connected'
                ? 'Backend connected and responsive'
                : connectionStatus === 'connecting'
                ? 'Connecting to backend...'
                : 'Backend unreachable.'
            }
          >
            {connectionStatus === 'connected' && (
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                <span className="hidden xs:inline sm:inline">Connected</span>
              </>
            )}
            {connectionStatus === 'connecting' && (
              <>
                <Loader2 size={12} className="animate-spin text-amber-600 shrink-0" />
                <span className="hidden sm:inline">Connecting...</span>
              </>
            )}
            {connectionStatus === 'disconnected' && (
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0" />
                <span className="hidden sm:inline">Offline</span>
              </>
            )}
          </div>

          {/* Refresh button — icon-only on mobile */}
          <button
            onClick={onRefreshAll}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-xl border border-slate-200 bg-white text-xs font-medium text-slate-700 hover:text-slate-900 hover:border-slate-300 hover:bg-slate-50 disabled:opacity-50 transition-all shadow-2xs"
            title="Refresh dashboard data"
          >
            <RefreshCw
              size={13}
              className={cn('text-slate-500', isRefreshing && 'animate-spin text-blue-600')}
            />
            <span className="hidden sm:inline">Refresh</span>
          </button>

          {/* Marketing site link */}
          <Link
            to="/"
            className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 px-2 sm:px-2.5 py-1.5 rounded-xl border border-transparent hover:border-slate-200 transition-all"
          >
            <ArrowLeft size={13} />
            <span className="hidden sm:inline">Overview</span>
          </Link>
        </div>
      </div>
    </header>
  );
};
