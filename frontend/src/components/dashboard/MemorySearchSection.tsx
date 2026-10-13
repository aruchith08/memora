import React, { useState } from 'react';
import { Search, Loader2, X, Sparkles, AlertCircle, Calendar, Tag } from 'lucide-react';
import { MemorySearchResult } from '../../types/api';
import { api, ApiError } from '../../services/api';

export const MemorySearchSection: React.FC = () => {
  const [query, setQuery] = useState('');
  const [limit, setLimit] = useState(5);
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<MemorySearchResult[] | null>(null);
  const [lastExecutedQuery, setLastExecutedQuery] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;

    setIsSearching(true);
    setError(null);

    try {
      const response = await api.searchMemories(trimmed, limit);
      setResults(response.results);
      setLastExecutedQuery(trimmed);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail || err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to search memories.');
      }
      setResults(null);
    } finally {
      setIsSearching(false);
    }
  };

  const handleClear = () => {
    setQuery('');
    setResults(null);
    setError(null);
    setLastExecutedQuery('');
  };

  return (
    <div className="p-5 rounded-xl border border-surface-border bg-white shadow-card">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-accent-blue/10 border border-accent-blue/20 flex items-center justify-center">
            <Search size={14} className="text-accent-blue" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-ink-primary">Semantic Memory Search</h3>
            <p className="text-[11px] text-ink-muted">
              FastEmbed vector similarity via Qdrant · Demo identity scoped
            </p>
          </div>
        </div>
      </div>

      {/* Search Input Form */}
      <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-2.5 mt-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search memories by natural meaning (e.g. 'flight details', 'exam schedule')..."
            className="w-full pl-9 pr-8 py-2 text-xs rounded-lg border border-surface-border bg-surface-hover/30 text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-1 focus:ring-accent-blue focus:border-accent-blue transition-colors"
          />
          {query && (
            <button
              type="button"
              onClick={handleClear}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-muted hover:text-ink-primary p-0.5"
              aria-label="Clear search"
            >
              <X size={13} />
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="px-2.5 py-2 text-xs rounded-lg border border-surface-border bg-white text-ink-secondary focus:outline-none focus:border-accent-blue"
            title="Max results to retrieve"
          >
            <option value={5}>Top 5</option>
            <option value={10}>Top 10</option>
            <option value={20}>Top 20</option>
          </select>

          <button
            type="submit"
            disabled={isSearching || !query.trim()}
            className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-ink-primary text-canvas text-xs font-medium hover:bg-ink-secondary disabled:opacity-50 transition-colors shrink-0"
          >
            {isSearching ? (
              <>
                <Loader2 size={13} className="animate-spin" />
                <span>Searching...</span>
              </>
            ) : (
              <span>Search</span>
            )}
          </button>
        </div>
      </form>

      {/* Error state */}
      {error && (
        <div className="mt-4 p-3 rounded-lg border border-rose-200 bg-rose-50 text-xs text-rose-800 flex items-start gap-2">
          <AlertCircle size={14} className="shrink-0 mt-0.5 text-rose-600" />
          <div className="flex-1">
            <p className="font-medium">Search error</p>
            <p className="mt-0.5 text-[11px]">{error}</p>
          </div>
        </div>
      )}

      {/* Results View */}
      {results !== null && !error && (
        <div className="mt-4 pt-3 border-t border-surface-border">
          <div className="flex items-center justify-between mb-3 text-xs text-ink-muted">
            <span>
              {results.length} {results.length === 1 ? 'match' : 'matches'} for "{lastExecutedQuery}"
            </span>
            <button
              onClick={handleClear}
              className="text-xs text-ink-muted hover:text-ink-primary underline"
            >
              Clear results
            </button>
          </div>

          {results.length === 0 ? (
            <div className="p-4 rounded-lg border border-dashed border-surface-border text-center bg-surface-muted/10">
              <p className="text-xs text-ink-secondary">
                No semantic matches found for "{lastExecutedQuery}".
              </p>
              <p className="mt-1 text-[11px] text-ink-muted">
                Try querying with different terms or check if memories exist in your feed.
              </p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {results.map((item) => {
                const scorePercent = Math.round(item.score * 100);
                const source = item.payload?.source || 'unknown';
                const createdAt = item.payload?.created_at
                  ? new Date(item.payload.created_at).toLocaleDateString(undefined, {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                  : null;

                return (
                  <div
                    key={item.id}
                    className="p-3 rounded-lg border border-surface-border bg-surface-hover/20 hover:border-surface-hover transition-colors"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-xs font-medium text-ink-primary leading-relaxed flex-1">
                        {item.text}
                      </p>
                      {/* Similarity score pill */}
                      <span
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-accent-blue/10 text-accent-blue shrink-0 border border-accent-blue/20"
                        title={`Cosine Similarity Score: ${item.score.toFixed(4)}`}
                      >
                        <Sparkles size={10} />
                        {scorePercent}% match
                      </span>
                    </div>

                    <div className="mt-2 flex items-center gap-3 text-[10px] text-ink-muted">
                      <span className="flex items-center gap-1">
                        <Tag size={10} />
                        <span className="font-mono">{source}</span>
                      </span>
                      {createdAt && (
                        <span className="flex items-center gap-1">
                          <Calendar size={10} />
                          <span>{createdAt}</span>
                        </span>
                      )}
                      <span className="font-mono text-ink-faint truncate max-w-[120px]" title={item.id}>
                        id: {item.id.slice(0, 8)}...
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
