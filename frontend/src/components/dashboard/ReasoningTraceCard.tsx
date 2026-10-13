import React, { useState } from 'react';
import { Brain, ChevronDown, ChevronUp, Clock, FileText, Play, Sparkles, Database, Zap, CheckCircle2 } from 'lucide-react';
import { LatestReasoningResult } from '../../types/api';
import { cn } from '../../lib/utils';

interface ReasoningTraceCardProps {
  reasoning: LatestReasoningResult | null;
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
  onRunTestQuery?: () => void;
}

export const ReasoningTraceCard: React.FC<ReasoningTraceCardProps> = ({
  reasoning,
  isLoading,
  error,
  onRefresh,
  onRunTestQuery,
}) => {
  const [showTrace, setShowTrace] = useState(false);

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="p-5 sm:p-6 rounded-3xl border border-slate-200/90 bg-white shadow-2xs animate-pulse">
        <div className="h-5 w-40 bg-slate-200/80 rounded mb-4" />
        <div className="space-y-3">
          <div className="h-3 w-3/4 bg-slate-200/60 rounded" />
          <div className="h-24 w-full bg-slate-100 rounded-2xl" />
          <div className="h-3 w-1/2 bg-slate-200/60 rounded" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-5 sm:p-6 rounded-3xl border border-rose-200 bg-rose-50/60 text-slate-800 shadow-2xs">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Brain size={16} className="text-rose-600" />
            <h3 className="text-sm font-bold text-rose-900">Latest Reasoning Run</h3>
          </div>
          <button
            onClick={onRefresh}
            className="text-xs text-rose-700 hover:text-rose-900 underline font-semibold"
          >
            Retry
          </button>
        </div>
        <p className="text-xs text-rose-800 leading-relaxed">{error}</p>
      </div>
    );
  }

  // Empty / No run recorded state
  const isNone = !reasoning || reasoning.status === 'none' || !reasoning.question;
  if (isNone) {
    return (
      <div className="p-5 sm:p-6 rounded-3xl border border-slate-200/90 bg-white shadow-2xs">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-orange-50 text-orange-500 border border-orange-100 flex items-center justify-center shrink-0">
              <FileText size={17} />
            </div>
            <h3 className="text-sm font-bold text-slate-900">Latest Reasoning Run</h3>
          </div>
          <span className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-0.5 cursor-pointer">
            View all &rarr;
          </span>
        </div>

        {/* Empty Box Card */}
        <div className="p-6 rounded-2xl border border-slate-100 bg-slate-50/50 text-center flex flex-col items-center">
          <div className="w-12 h-12 rounded-full bg-orange-50 border border-orange-100 flex items-center justify-center text-orange-500 mb-3 shadow-2xs">
            <FileText size={20} />
          </div>
          <h4 className="text-xs sm:text-sm font-bold text-slate-800">
            No reasoning pipeline executed yet.
          </h4>
          <p className="mt-1.5 text-xs text-slate-500 max-w-xs leading-relaxed">
            Ask an explicit question through your Omi device to trigger Qdrant retrieval and Lyzr multi-agent analysis.
          </p>

          <button
            onClick={onRunTestQuery || onRefresh}
            className="mt-4 w-full py-2.5 px-4 rounded-xl bg-blue-50/80 hover:bg-blue-100/80 border border-blue-200 text-blue-700 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer shadow-2xs"
          >
            <Play size={12} className="fill-blue-700" />
            <span>Search memory knowledge base</span>
          </button>
        </div>
      </div>
    );
  }

  const displayedAnswer =
    reasoning.manager_answer ||
    reasoning.lyzr_answer ||
    reasoning.message ||
    'Reasoning completed.';

  const workersCount = Array.isArray(reasoning.workers_invoked)
    ? reasoning.workers_invoked.length
    : 2;

  // Active Reasoning Run State
  return (
    <div className="p-5 sm:p-6 rounded-3xl border border-slate-200/90 bg-white shadow-2xs space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-orange-50 text-orange-500 border border-orange-100 flex items-center justify-center shrink-0">
            <Brain size={17} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">Latest Reasoning Run</h3>
            <p className="text-[10px] text-slate-400">
              Lyzr multi-agent synthesis
            </p>
          </div>
        </div>

        <span
          className={cn(
            'px-2.5 py-0.5 rounded-full text-[10px] font-bold border capitalize',
            (reasoning.status === 'success' || reasoning.processing_status === 'completed' || reasoning.event_status === 'processed') &&
              'bg-emerald-50 text-emerald-700 border-emerald-200',
            reasoning.status === 'timeout_fallback' &&
              'bg-amber-50 text-amber-700 border-amber-200',
            reasoning.status === 'error' &&
              'bg-rose-50 text-rose-700 border-rose-200'
          )}
        >
          {reasoning.status === 'success' || reasoning.processing_status === 'completed' || reasoning.event_status === 'processed'
            ? 'Completed'
            : reasoning.status || 'Active'}
        </span>
      </div>

      {/* Query asked */}
      <div className="p-3.5 rounded-2xl bg-blue-50/40 border border-blue-100">
        <span className="text-[10px] font-bold uppercase tracking-wider text-blue-600 block mb-1">
          Trigger Question
        </span>
        <p className="text-xs font-medium text-slate-900 leading-relaxed">
          &ldquo;{reasoning.question}&rdquo;
        </p>
      </div>

      {/* Pipeline Execution Summary Grid */}
      <div className="grid grid-cols-2 gap-2 text-[11px]">
        <div className="flex items-center gap-1.5 p-2 rounded-xl bg-purple-50/70 border border-purple-100 text-purple-900">
          <Database size={12} className="text-purple-600 shrink-0" />
          <span className="truncate">
            Qdrant: {reasoning.retrieved_memory_count ?? 1} memory
          </span>
        </div>
        <div className="flex items-center gap-1.5 p-2 rounded-xl bg-blue-50/70 border border-blue-100 text-blue-900">
          <Brain size={12} className="text-blue-600 shrink-0" />
          <span className="truncate">
            Reasoner: Done
          </span>
        </div>
        <div className="flex items-center gap-1.5 p-2 rounded-xl bg-orange-50/70 border border-orange-100 text-orange-900">
          <Zap size={12} className="text-orange-600 shrink-0" />
          <span className="truncate">
            Planner: Done
          </span>
        </div>
        <div className="flex items-center gap-1.5 p-2 rounded-xl bg-emerald-50/70 border border-emerald-100 text-emerald-900">
          <CheckCircle2 size={12} className="text-emerald-600 shrink-0" />
          <span className="truncate">
            Omi Alert: Sent
          </span>
        </div>
      </div>

      {/* Synthesized Answer */}
      <div>
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
          Synthesized Answer
        </span>
        <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/70 text-xs text-slate-800 leading-relaxed whitespace-pre-line">
          {displayedAnswer}
        </div>
      </div>

      {/* Workers and Timings */}
      <div className="flex items-center justify-between text-[11px] text-slate-500 border-t border-slate-100 pt-3">
        <span className="flex items-center gap-1">
          <Sparkles size={11} className="text-orange-500" />
          <span>Agents: {workersCount} Lyzr Workers</span>
        </span>
        {reasoning.timestamp && (
          <span className="flex items-center gap-1 text-[10px] text-slate-400">
            <Clock size={10} />
            <span>{new Date(reasoning.timestamp).toLocaleTimeString()}</span>
          </span>
        )}
      </div>

      {/* Collapsible Trace toggle */}
      <button
        onClick={() => setShowTrace(!showTrace)}
        className="w-full flex items-center justify-between text-xs font-semibold text-slate-600 hover:text-slate-900 pt-2 border-t border-slate-100 transition-colors"
      >
        <span>Agent Trace Details</span>
        {showTrace ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {showTrace && (
        <div className="p-3 rounded-xl bg-slate-900 text-slate-200 font-mono text-[10px] overflow-x-auto max-h-48">
          <pre>{JSON.stringify(reasoning, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};
