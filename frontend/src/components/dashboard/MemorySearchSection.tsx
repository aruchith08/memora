import React, { useState } from 'react';
import { Search, Loader2, X, Sparkles, Calendar, Tag, CheckCircle2 } from 'lucide-react';
import { MemorySearchResult } from '../../types/api';
import { api, ApiError } from '../../services/api';

const DEFAULT_SUGGESTIONS = [
  'flights to SF',
  'MSF class',
  'grocery list',
  'project ideas',
  'sprint review',
  'meetings',
  'reminders',
];

interface MemorySearchSectionProps {
  onSearchResultSelect?: (result: MemorySearchResult) => void;
}

export const MemorySearchSection: React.FC<MemorySearchSectionProps> = ({
  onSearchResultSelect,
}) => {
  const [query, setQuery] = useState('');
  const [limit, setLimit] = useState(5);
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<MemorySearchResult[] | null>(null);
  const [lastExecutedQuery, setLastExecutedQuery] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const performSearch = async (searchQuery: string, searchLimit: number) => {
    const trimmed = searchQuery.trim();
    if (!trimmed) return;

    setIsSearching(true);
    setError(null);

    try {
      const response = await api.searchMemories(trimmed, searchLimit);
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

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    performSearch(query, limit);
  };

  const handleChipClick = (suggestion: string) => {
    setQuery(suggestion);
    performSearch(suggestion, limit);
  };

  const handleClear = () => {
    setQuery('');
    setResults(null);
    setError(null);
    setLastExecutedQuery('');
  };

  return (
    <div className="relative overflow-hidden rounded-3xl border border-blue-100 bg-gradient-to-b from-blue-50/80 via-blue-50/30 to-white p-6 sm:p-8 text-center shadow-2xs">
      {/* Title & Subtitle */}
      <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
        Search Your <span className="text-blue-600">Memories</span>
      </h1>
      <p className="mt-1.5 text-xs sm:text-sm text-slate-500">
        Find anything from your conversations using natural language.
      </p>

      {/* Main Search Input Form */}
      <form
        onSubmit={handleFormSubmit}
        className="mt-6 max-w-3xl mx-auto flex items-center gap-2 bg-white border border-slate-200/90 rounded-2xl p-2 sm:p-2.5 shadow-sm focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-100 transition-all"
      >
        <Search size={18} className="text-blue-600 ml-2.5 shrink-0" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder='Search memories (e.g. "flights to SF", "MSF class", "grocery list")'
          className="flex-1 bg-transparent px-2.5 py-1 text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-none"
        />

        {query && (
          <button
            type="button"
            onClick={handleClear}
            className="p-1 rounded-full text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            title="Clear search query"
          >
            <X size={14} />
          </button>
        )}

        <div className="h-6 w-px bg-slate-200 mx-1 hidden sm:block" />

        {/* Limit Dropdown */}
        <select
          value={limit}
          onChange={(e) => {
            const newLimit = Number(e.target.value);
            setLimit(newLimit);
            if (lastExecutedQuery) {
              performSearch(lastExecutedQuery, newLimit);
            }
          }}
          className="bg-transparent border-0 text-xs font-semibold text-slate-600 focus:outline-none px-2 py-1 cursor-pointer hover:text-slate-900"
          title="Number of results"
        >
          <option value={3}>Top 3</option>
          <option value={5}>Top 5</option>
          <option value={10}>Top 10</option>
        </select>

        {/* Submit Search Button */}
        <button
          type="submit"
          disabled={isSearching || !query.trim()}
          className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs sm:text-sm font-semibold transition-colors disabled:opacity-50 shadow-xs cursor-pointer shrink-0"
        >
          {isSearching ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Search size={16} />
          )}
          <span>Search</span>
        </button>
      </form>

      {/* Query Suggestion Chips */}
      <div className="mt-4 flex flex-wrap items-center justify-center gap-2 max-w-3xl mx-auto">
        {DEFAULT_SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => handleChipClick(suggestion)}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-white border border-slate-200 text-xs text-slate-600 hover:border-blue-300 hover:text-blue-600 hover:bg-blue-50/50 transition-all shadow-2xs cursor-pointer"
          >
            <Search size={11} className="text-slate-400" />
            <span>{suggestion}</span>
          </button>
        ))}
      </div>

      {/* Error Message */}
      {error && (
        <div className="mt-4 max-w-2xl mx-auto p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700 text-left">
          {error}
        </div>
      )}

      {/* Search Results Expansion */}
      {results !== null && (
        <div className="mt-6 text-left max-w-3xl mx-auto border-t border-blue-100/80 pt-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Sparkles size={15} className="text-blue-600" />
              <h3 className="text-xs sm:text-sm font-bold text-slate-800">
                Retrieved {results.length} semantic matches for &ldquo;{lastExecutedQuery}&rdquo;
              </h3>
            </div>
            <button
              onClick={handleClear}
              className="text-xs text-slate-500 hover:text-slate-800 underline flex items-center gap-1 font-medium"
            >
              <X size={12} />
              Clear results
            </button>
          </div>

          {results.length === 0 ? (
            <div className="p-6 rounded-2xl bg-white border border-slate-200 text-center text-xs text-slate-500">
              No matching memories found in Qdrant for this query. Try another keyword or phrase.
            </div>
          ) : (
            <div className="space-y-2.5">
              {results.map((res) => {
                const matchPct = Math.round(res.score * 100);
                const scoreColor =
                  matchPct >= 70
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    : matchPct >= 50
                    ? 'bg-blue-50 text-blue-700 border-blue-200'
                    : 'bg-slate-100 text-slate-600 border-slate-200';

                return (
                  <div
                    key={res.id}
                    onClick={() => onSearchResultSelect?.(res)}
                    className="p-3.5 rounded-2xl bg-white border border-slate-200/90 shadow-2xs hover:border-blue-300 hover:shadow-xs transition-all cursor-pointer"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-xs sm:text-sm font-medium text-slate-900 leading-relaxed flex-1">
                        {res.text}
                      </p>
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold border shrink-0 ${scoreColor}`}
                      >
                        <CheckCircle2 size={11} />
                        {matchPct}% match
                      </span>
                    </div>

                    {res.payload && (
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] text-slate-500 border-t border-slate-100 pt-2">
                        {res.payload.source && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-mono">
                            <Tag size={9} />
                            {String(res.payload.source)}
                          </span>
                        )}
                        {res.payload.created_at && (
                          <span className="inline-flex items-center gap-1">
                            <Calendar size={10} />
                            {new Date(String(res.payload.created_at)).toLocaleDateString()}
                          </span>
                        )}
                        <span className="ml-auto font-mono text-[9px] text-slate-400">
                          ID: {res.id.slice(0, 8)}
                        </span>
                      </div>
                    )}
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
