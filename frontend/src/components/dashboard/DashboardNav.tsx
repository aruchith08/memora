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
    <header className="sticky top-0 z-40 bg-canvas/95 backdrop-blur-sm border-b border-surface-border">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Left: Brand & Dashboard title */}
        <div className="flex items-center gap-3">
          <Link
            to="/"
            className="text-ink-primary font-semibold text-lg tracking-tight hover:opacity-80 transition-opacity"
          >
            Memora
          </Link>
          <span className="text-surface-border">/</span>
          <span className="text-xs font-medium text-ink-secondary bg-surface-muted px-2 py-0.5 rounded border border-surface-border">
            Console
          </span>
        </div>

        {/* Right: Status badge, refresh button & back link */}
        <div className="flex items-center gap-3 sm:gap-4">
          {/* Connection status badge */}
          <div
            className={cn(
              'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors',
              connectionStatus === 'connected' &&
                'bg-emerald-50 text-emerald-800 border-emerald-200/80',
              connectionStatus === 'connecting' &&
                'bg-amber-50 text-amber-800 border-amber-200/80',
              connectionStatus === 'disconnected' &&
                'bg-rose-50 text-rose-800 border-rose-200/80'
            )}
            title={
              connectionStatus === 'connected'
                ? 'Backend connected and responsive at http://127.0.0.1:8000'
                : connectionStatus === 'connecting'
                ? 'Connecting to backend...'
                : 'Backend unreachable. Verify uvicorn server is running on port 8000.'
            }
          >
            {connectionStatus === 'connected' && (
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="hidden sm:inline">Backend</span> Connected
              </>
            )}
            {connectionStatus === 'connecting' && (
              <>
                <Loader2 size={12} className="animate-spin text-amber-600" />
                Connecting...
              </>
            )}
            {connectionStatus === 'disconnected' && (
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                <span className="hidden sm:inline">Backend</span> Offline
              </>
            )}
          </div>

          {/* Refresh all button */}
          <button
            onClick={onRefreshAll}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-surface-border bg-white text-xs font-medium text-ink-secondary hover:text-ink-primary hover:border-surface-hover disabled:opacity-50 transition-colors"
            title="Refresh dashboard data"
          >
            <RefreshCw
              size={13}
              className={cn(isRefreshing && 'animate-spin text-accent-blue')}
            />
            <span className="hidden sm:inline">Refresh</span>
          </button>

          {/* Link back to marketing site */}
          <Link
            to="/"
            className="inline-flex items-center gap-1 text-xs text-ink-muted hover:text-ink-primary transition-colors py-1.5 pl-2"
          >
            <ArrowLeft size={13} />
            <span className="hidden sm:inline">Marketing Site</span>
          </Link>
        </div>
      </div>
    </header>
  );
};
