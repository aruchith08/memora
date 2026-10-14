import React, { useState } from 'react';
import { FileText, RefreshCw, Calendar, Tag, AlertCircle, Trash2, Loader2, MessageSquare, Search } from 'lucide-react';
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
    <div className="p-4 sm:p-5 md:p-6 rounded-3xl border border-slate-200/90 bg-white shadow-2xs">
      {/* Section Header */}
      <div className="flex items-center justify-between gap-2 pb-4 border-b border-slate-100">
        <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
          <div className="w-8 sm:w-9 h-8 sm:h-9 rounded-xl bg-orange-50 text-orange-500 border border-orange-100 flex items-center justify-center shrink-0">
            <FileText size={16} />
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-bold text-slate-900 leading-tight">Recent Voice Memories</h3>
            <p className="text-[10px] sm:text-[11px] text-slate-400 leading-tight truncate">
              Qdrant vector store
            </p>
          </div>
        </div>

        {/* Header Controls */}
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
          <select
            value={limit}
            onChange={(e) => onLimitChange(Number(e.target.value))}
            className="px-2 sm:px-3 py-1.5 text-xs font-semibold rounded-xl border border-slate-200 bg-white text-slate-700 focus:outline-none focus:border-blue-400 cursor-pointer shadow-2xs"
            title="Max records to retrieve"
          >
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
          </select>

          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="p-2 rounded-xl border border-slate-200 bg-white text-slate-600 hover:text-slate-900 hover:bg-slate-50 disabled:opacity-50 transition-colors shadow-2xs"
            title="Refresh memories feed"
          >
            <RefreshCw size={13} className={cn(isLoading && 'animate-spin text-blue-600')} />
          </button>
        </div>
      </div>

      {/* Quick local search / filter */}
      {memories.length > 3 && (
        <div className="mt-3.5 relative">
          <Search size={13} className="absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            placeholder="Filter current memories..."
            className="w-full pl-8 pr-3 py-1.5 text-xs rounded-xl border border-slate-200 bg-slate-50/60 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-400 focus:bg-white transition-all"
          />
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="mt-4 p-4 rounded-xl border border-rose-200 bg-rose-50 text-xs text-rose-800 flex items-start gap-2.5">
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
              className="p-4 rounded-2xl border border-slate-100 bg-slate-50/50 animate-pulse space-y-2.5"
            >
              <div className="h-4 w-4/5 bg-slate-200/80 rounded" />
              <div className="h-3 w-1/3 bg-slate-200/60 rounded" />
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && memories.length === 0 && (
        <div className="mt-4 p-8 rounded-2xl border border-dashed border-slate-200 text-center bg-slate-50/50">
          <div className="w-10 h-10 rounded-xl bg-white border border-slate-200 mx-auto flex items-center justify-center mb-2.5 shadow-2xs">
            <FileText size={18} className="text-slate-400" />
          </div>
          <h4 className="text-xs font-bold text-slate-800">No memories recorded yet</h4>
          <p className="mt-1 text-xs text-slate-500 max-w-sm mx-auto leading-relaxed">
            Ambient conversations and audio notes received via Omi will be vectorized in real time and stored securely in Qdrant Cloud.
          </p>
        </div>
      )}

      {/* Populated Feed List */}
      {!isLoading && !error && memories.length > 0 && (
        <div className="mt-4 space-y-3">
          <div className="flex items-center justify-between text-[11px] text-slate-400 pb-0.5">
            <span>
              Showing {displayedMemories.length} of {count} memories
            </span>
            {effectiveUid && (
              <span className="font-mono text-[10px]">
                tenant: {effectiveUid.replace('demo_', '')}
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
              : 'Recent';

            // Extract tags or fallback
            const tags =
              mem.metadata && typeof mem.metadata.tags === 'string'
                ? mem.metadata.tags
                : mem.metadata && Array.isArray(mem.metadata.tags)
                ? mem.metadata.tags.join(', ')
                : null;

            return (
              <div
                key={mem.id}
                className="p-4 rounded-2xl border border-slate-200/90 bg-white hover:border-slate-300 hover:shadow-xs transition-all group"
              >
                {/* Main Text */}
                <p className="text-xs sm:text-sm font-medium text-slate-900 leading-relaxed">
                  {mem.text}
                </p>

                {/* Bottom Meta Row */}
                <div className="mt-3 flex flex-wrap items-center gap-2.5 text-[11px] text-slate-500 pt-2 border-t border-slate-100">
                  {/* Differentiated Source Pill */}
                  {(() => {
                    const src = (mem.source || (mem.metadata?.source as string) || '').toLowerCase();
                    const id = (mem.id || '').toLowerCase();
                    const isSynthetic = id.startsWith('a3b4c5d6') || id.includes('demo') || !!mem.metadata?.synthetic;
                    const isRealtime = src.includes('realtime') || src.includes('streaming');
                    const isManual = src.includes('manual') || src.includes('admin');

                    const badge = isSynthetic
                      ? { label: 'Demo memory', bg: 'bg-purple-50 text-purple-700 border-purple-200/70' }
                      : isRealtime
                      ? { label: 'Realtime transcript', bg: 'bg-blue-50 text-blue-700 border-blue-200/70' }
                      : isManual
                      ? { label: 'Manual entry', bg: 'bg-slate-100 text-slate-700 border-slate-200/70' }
                      : { label: 'Omi conversation', bg: 'bg-emerald-50 text-emerald-700 border-emerald-200/70' };

                    return (
                      <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-medium text-[10px] border', badge.bg)}>
                        <MessageSquare size={10} className="opacity-70" />
                        <span>{badge.label}</span>
                      </span>
                    );
                  })()}

                  {/* Timestamp */}
                  <span className="inline-flex items-center gap-1 text-slate-500">
                    <Calendar size={11} className="text-slate-400" />
                    <span>{formattedDate}</span>
                  </span>

                  {/* Tags */}
                  {tags && (
                    <span className="inline-flex items-center gap-1 text-slate-500 truncate max-w-[200px]" title={tags}>
                      <Tag size={11} className="text-slate-400" />
                      <span>{tags}</span>
                    </span>
                  )}

                  {/* ID & Forget Action Button */}
                  <div className="ml-auto flex items-center gap-2">
                    <span className="font-mono text-[10px] text-slate-400" title={mem.id}>
                      #{mem.id.slice(0, 6)}
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
                        className="p-1 rounded-md text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors disabled:opacity-50"
                        title="Forget this memory (Right to be Forgotten)"
                      >
                        {deletingId === mem.id ? (
                          <Loader2 size={12} className="animate-spin text-rose-500" />
                        ) : (
                          <Trash2 size={12} />
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
