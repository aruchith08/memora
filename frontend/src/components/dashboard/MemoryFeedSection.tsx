import React, { useState } from 'react';
import { Database, RefreshCw, Calendar, Tag, AlertCircle, Trash2, Loader2 } from 'lucide-react';
import { MemoryItem } from '../../types/api';
import { cn } from '../../lib/utils';

interface MemoryFeedSectionProps {
  memories: MemoryItem[];
  count: number;
  effectiveUid: string | null;
  isLoading: boolean;
  error: string | null;
  limit: number;
  onLimitChange: (limit: number) => void;
  onRefresh: () => void;
  onDeleteMemory?: (id: string) => Promise<void>;
}

export const MemoryFeedSection: React.FC<MemoryFeedSectionProps> = ({
  memories,
  count,
  effectiveUid,
  isLoading,
  error,
  limit,
  onLimitChange,
  onRefresh,
  onDeleteMemory,
}) => {
  const [filterText, setFilterText] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Filter memories locally by text if user types in quick filter
  const displayedMemories = filterText.trim()
    ? memories.filter((m) =>
        m.text.toLowerCase().includes(filterText.toLowerCase().trim())
      )
    : memories;

  return (
    <div className="p-5 rounded-xl border border-surface-border bg-white shadow-card">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-surface-border">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-accent-peach/10 border border-accent-peach/20 flex items-center justify-center">
            <Database size={14} className="text-accent-peach" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-ink-primary">Recent Voice Memories</h3>
            <p className="text-[11px] text-ink-muted">
              Descending chronological timeline from Qdrant vector store
            </p>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2 shrink-0">
          <select
            value={limit}
            onChange={(e) => onLimitChange(Number(e.target.value))}
            className="px-2.5 py-1.5 text-xs rounded-md border border-surface-border bg-white text-ink-secondary focus:outline-none focus:border-accent-blue"
            title="Max records to retrieve"
          >
            <option value={10}>Latest 10</option>
            <option value={20}>Latest 20</option>
            <option value={50}>Latest 50</option>
          </select>

          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="p-1.5 rounded-md border border-surface-border bg-white text-ink-secondary hover:text-ink-primary hover:border-surface-hover disabled:opacity-50 transition-colors"
            title="Refresh memories feed"
          >
            <RefreshCw size={13} className={cn(isLoading && 'animate-spin text-accent-blue')} />
          </button>
        </div>
      </div>

      {/* Quick local text filter */}
      {memories.length > 5 && (
        <div className="mt-3">
          <input
            type="text"
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            placeholder="Quick filter on current feed..."
            className="w-full px-3 py-1.5 text-xs rounded-md border border-surface-border bg-surface-hover/20 text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-1 focus:ring-accent-blue focus:border-accent-blue"
          />
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="mt-4 p-4 rounded-lg border border-rose-200 bg-rose-50 text-xs text-rose-800 flex items-start gap-2.5">
          <AlertCircle size={15} className="shrink-0 mt-0.5 text-rose-600" />
          <div className="flex-1">
            <p className="font-semibold text-rose-900">Failed to load memories</p>
            <p className="mt-0.5 text-[11px] leading-relaxed">{error}</p>
            <button
              onClick={onRefresh}
              className="mt-2 inline-flex items-center text-xs font-semibold text-rose-800 hover:text-rose-950 underline"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading && !error && (
        <div className="mt-4 space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="p-3.5 rounded-lg border border-surface-border bg-surface-muted/30 animate-pulse space-y-2"
            >
              <div className="h-3.5 w-4/5 bg-surface-muted rounded" />
              <div className="h-2.5 w-1/3 bg-surface-muted rounded" />
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && memories.length === 0 && (
        <div className="mt-4 p-8 rounded-lg border border-dashed border-surface-border text-center bg-surface-muted/10">
          <div className="w-10 h-10 rounded-xl bg-surface-muted border border-surface-border mx-auto flex items-center justify-center mb-3">
            <Database size={18} className="text-ink-muted" />
          </div>
          <h4 className="text-xs font-semibold text-ink-primary">No memories recorded yet</h4>
          <p className="mt-1 text-xs text-ink-muted max-w-sm mx-auto leading-relaxed">
            Conversation transcripts sent by Omi devices via webhook will be embedded with FastEmbed and indexed in your local Qdrant collection.
          </p>
        </div>
      )}

      {/* Populated Feed */}
      {!isLoading && !error && memories.length > 0 && (
        <div className="mt-4 space-y-2.5">
          <div className="flex items-center justify-between text-[11px] text-ink-muted pb-1">
            <span>
              Showing {displayedMemories.length} of {count} retrieved records
            </span>
            {effectiveUid && (
              <span className="font-mono text-[10px]">
                uid: {effectiveUid}
              </span>
            )}
          </div>

          {displayedMemories.map((mem) => {
            const formattedDate = mem.created_at
              ? new Date(mem.created_at).toLocaleString(undefined, {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })
              : 'Unknown date';

            return (
              <div
                key={mem.id}
                className="p-3.5 rounded-lg border border-surface-border bg-white hover:border-surface-hover hover:shadow-xs transition-all"
              >
                <p className="text-xs font-normal text-ink-primary leading-relaxed">
                  {mem.text}
                </p>

                <div className="mt-2.5 flex flex-wrap items-center gap-2.5 text-[10px] text-ink-muted border-t border-surface-border/50 pt-2">
                  {/* Source tag */}
                  <span className="inline-flex items-center gap-1 font-mono px-1.5 py-0.5 rounded bg-surface-muted text-ink-secondary border border-surface-border">
                    <Tag size={9} />
                    <span>{mem.source || 'voice'}</span>
                  </span>

                  {/* Timestamp */}
                  <span className="inline-flex items-center gap-1 text-ink-muted">
                    <Calendar size={10} />
                    <span>{formattedDate}</span>
                  </span>

                  {/* Safe metadata keys preview if present */}
                  {mem.metadata && Object.keys(mem.metadata).length > 0 && (
                    <span className="text-[10px] text-ink-faint truncate max-w-[200px]" title={JSON.stringify(mem.metadata)}>
                      meta: {Object.entries(mem.metadata).map(([k, v]) => `${k}=${v}`).join(', ')}
                    </span>
                  )}

                  {/* Memory ID hash & Forget Button */}
                  <div className="ml-auto flex items-center gap-2">
                    <span className="font-mono text-[9px] text-ink-faint" title={mem.id}>
                      {mem.id.slice(0, 8)}
                    </span>
                    {onDeleteMemory && (
                      <button
                        onClick={async () => {
                          if (window.confirm('Forget this memory permanently from Qdrant vector storage?')) {
                            setDeletingId(mem.id);
                            try {
                              await onDeleteMemory(mem.id);
                            } finally {
                              setDeletingId(null);
                            }
                          }
                        }}
                        disabled={deletingId === mem.id}
                        className="p-1 rounded text-ink-muted hover:text-rose-600 hover:bg-rose-50 transition-colors disabled:opacity-50"
                        title="Forget this memory"
                      >
                        {deletingId === mem.id ? (
                          <Loader2 size={11} className="animate-spin text-rose-500" />
                        ) : (
                          <Trash2 size={11} />
                        )}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
