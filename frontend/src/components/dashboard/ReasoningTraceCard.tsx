import React, { useState } from 'react';
import { Brain, ChevronDown, ChevronUp, Bell, Users, Clock, FileText, CheckCircle2, AlertCircle, HelpCircle } from 'lucide-react';
import { LatestReasoningResult } from '../../types/api';
import { cn } from '../../lib/utils';

interface ReasoningTraceCardProps {
  reasoning: LatestReasoningResult | null;
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export const ReasoningTraceCard: React.FC<ReasoningTraceCardProps> = ({
  reasoning,
  isLoading,
  error,
  onRefresh,
}) => {
  const [showTrace, setShowTrace] = useState(false);

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="p-5 rounded-xl border border-surface-border bg-white shadow-card animate-pulse">
        <div className="h-4 w-40 bg-surface-muted rounded mb-4" />
        <div className="space-y-3">
          <div className="h-3 w-3/4 bg-surface-muted rounded" />
          <div className="h-16 w-full bg-surface-muted rounded" />
          <div className="h-3 w-1/2 bg-surface-muted rounded" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-5 rounded-xl border border-rose-200 bg-rose-50/50 text-ink-primary shadow-card">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Brain size={16} className="text-rose-600" />
            <h3 className="text-sm font-semibold text-rose-900">Latest Reasoning Run</h3>
          </div>
          <button
            onClick={onRefresh}
            className="text-xs text-rose-700 hover:text-rose-900 underline font-medium"
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
      <div className="p-5 rounded-xl border border-surface-border bg-white shadow-card">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Brain size={16} className="text-accent-peach" />
            <h3 className="text-sm font-semibold text-ink-primary">Latest Reasoning Run</h3>
          </div>
          <span className="text-[11px] font-mono text-ink-muted">Recorded audit log</span>
        </div>
        <div className="p-4 rounded-lg border border-dashed border-surface-border bg-surface-muted/20 text-center">
          <p className="text-xs text-ink-secondary">
            {reasoning?.message || 'No reasoning pipeline executed yet.'}
          </p>
          <p className="mt-1 text-[11px] text-ink-muted">
            Ask an explicit question through your Omi device to trigger Qdrant retrieval and Lyzr multi-agent analysis.
          </p>
        </div>
      </div>
    );
  }

  const answer = reasoning.manager_answer || reasoning.lyzr_answer;
  const workers = reasoning.workers_invoked || [];
  const trace = reasoning.execution_trace || [];
  const formattedTime = reasoning.timestamp
    ? new Date(reasoning.timestamp).toLocaleString(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short',
      })
    : null;

  // Helper to determine honest delegation status
  const getDelegationStatus = () => {
    if (reasoning.orchestration_mode === 'deterministic_sequential') {
      return {
        label: 'Sequential collaboration',
        className: 'bg-indigo-50 text-indigo-800 border-indigo-200',
        icon: Users,
        title: 'Backend-orchestrated sequential execution across specialized workers (MEMORA Reasoner → MEMORA Action Planner).',
      };
    }
    if (reasoning.delegation_observed === true) {
      return {
        label: 'Delegation verified',
        className: 'bg-emerald-50 text-emerald-800 border-emerald-200',
        icon: CheckCircle2,
        title: 'Lyzr Manager verified delegation to worker agent via live telemetry.',
      };
    }
    if (reasoning.telemetry_status === 'unavailable') {
      return {
        label: 'Telemetry unconfirmed',
        className: 'bg-amber-50 text-amber-800 border-amber-200',
        icon: HelpCircle,
        title: 'Multi-agent telemetry stream was unavailable during inference; delegation status cannot be conclusively proven from telemetry alone.',
      };
    }
    if (reasoning.telemetry_status === 'collected' && workers.length === 0) {
      return {
        label: 'No delegation observed',
        className: 'bg-surface-muted text-ink-secondary border-surface-border',
        icon: AlertCircle,
        title: 'Lyzr Manager processed the query directly without invoking worker specialists.',
      };
    }
    return {
      label: 'Status unavailable',
      className: 'bg-surface-muted text-ink-muted border-surface-border',
      icon: HelpCircle,
      title: undefined,
    };
  };

  // Helper to determine safe notification diagnostics
  const getNotificationDiagnostics = () => {
    const rawStatus = (reasoning.notification_status || '').toLowerCase().trim();
    const statusCode = reasoning.notification_status_code;

    if (!rawStatus) {
      return {
        label: 'Notification: not recorded',
        detail: null,
        className: 'bg-surface-muted text-ink-muted border-surface-border',
      };
    }

    if (rawStatus === 'sent') {
      return {
        label: statusCode ? `Notification sent (${statusCode})` : 'Notification sent',
        detail: 'Delivered to Omi user',
        className: 'bg-emerald-50 text-emerald-800 border-emerald-200',
      };
    }

    if (rawStatus === 'failed') {
      let detail = 'Delivery failed';
      if (statusCode === 404) {
        detail = 'Recipient resource or device UID unverified (HTTP 404)';
      } else if (statusCode === 401 || statusCode === 403) {
        detail = `Authentication error (HTTP ${statusCode})`;
      } else if (statusCode) {
        detail = `Integration error (HTTP ${statusCode})`;
      } else if (reasoning.notification_error && reasoning.notification_error.toLowerCase().includes('timeout')) {
        detail = 'Delivery timed out';
      }

      return {
        label: statusCode ? `Notification failed (${statusCode})` : 'Notification failed',
        detail,
        className: 'bg-rose-50 text-rose-800 border-rose-200',
      };
    }

    if (rawStatus === 'skipped') {
      let detail = 'Notification skipped';
      if (reasoning.notification_error && reasoning.notification_error.toLowerCase().includes('empty')) {
        detail = 'No content to notify';
      }
      return {
        label: 'Notification skipped',
        detail,
        className: 'bg-surface-muted text-ink-secondary border-surface-border',
      };
    }

    // Pending or any other status
    return {
      label: `Notification: ${rawStatus}`,
      detail: null,
      className: 'bg-surface-muted text-ink-muted border-surface-border',
    };
  };

  const delegationInfo = getDelegationStatus();
  const notifInfo = getNotificationDiagnostics();
  const DelegationIcon = delegationInfo.icon;

  const workerNames = workers.map(w => (typeof w === 'string' ? w : w?.agent_name || w?.agent_id || 'Worker'));

  return (
    <div className="p-5 rounded-xl border border-surface-border bg-white shadow-card">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-surface-border">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-accent-peach/10 border border-accent-peach/20 flex items-center justify-center">
            <Brain size={14} className="text-accent-peach" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-ink-primary">Latest Recorded Reasoning</h3>
            <p className="text-[11px] text-ink-muted">
              Snapshot from previous pipeline run · Lyzr multi-agent orchestration
            </p>
          </div>
        </div>

        {formattedTime && (
          <div className="flex items-center gap-1.5 text-xs text-ink-muted shrink-0">
            <Clock size={12} />
            <span>{formattedTime}</span>
          </div>
        )}
      </div>

      {/* Query & Answer */}
      <div className="mt-4 space-y-3">
        <div className="p-3 rounded-lg border border-surface-border bg-surface-muted/20">
          <p className="text-[11px] font-medium text-ink-muted uppercase tracking-wider mb-1">
            Voice Query Evaluated
          </p>
          <p className="text-sm font-medium text-ink-primary">
            "{reasoning.question}"
          </p>
        </div>

        <div className="p-3.5 rounded-lg border border-accent-blue/20 bg-accent-blue/5">
          <p className="text-[11px] font-semibold text-accent-blue uppercase tracking-wider mb-1">
            Synthesized Answer
          </p>
          <p className="text-sm text-ink-primary leading-relaxed whitespace-pre-wrap">
            {answer || 'No answer generated.'}
          </p>
        </div>
      </div>

      {/* Observability metadata pills */}
      <div className="mt-4 pt-3 border-t border-surface-border flex flex-wrap gap-2 items-center text-xs">
        {/* Memory count */}
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-surface-muted text-ink-secondary border border-surface-border">
          <FileText size={12} />
          <span>{reasoning.retrieved_memory_count ?? 0} memories referenced</span>
        </span>

        {/* Workers invoked */}
        {workerNames.length > 0 && (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-muted text-ink-secondary border border-surface-border">
            <Users size={12} />
            <span>Workers: {workerNames.join(', ')}</span>
          </span>
        )}

        {/* Honest Delegation status */}
        <span
          className={cn(
            'inline-flex items-center gap-1 px-2.5 py-1 rounded-md border text-xs',
            delegationInfo.className
          )}
          title={delegationInfo.title}
        >
          <DelegationIcon size={12} />
          <span>{delegationInfo.label}</span>
        </span>

        {/* Notification diagnostics */}
        <span
          className={cn(
            'inline-flex items-center gap-1 px-2.5 py-1 rounded-md border text-xs',
            notifInfo.className
          )}
          title={notifInfo.detail || undefined}
        >
          <Bell size={12} />
          <span>{notifInfo.label}</span>
          {notifInfo.detail && (
            <span className="hidden sm:inline opacity-75 font-normal">
              · {notifInfo.detail}
            </span>
          )}
        </span>
      </div>

      {/* Execution trace dropdown */}
      {trace.length > 0 && (
        <div className="mt-3 pt-3 border-t border-surface-border">
          <button
            onClick={() => setShowTrace(!showTrace)}
            className="flex items-center justify-between w-full text-xs font-medium text-ink-secondary hover:text-ink-primary transition-colors py-1"
          >
            <span>Agent Execution Trace ({trace.length} steps)</span>
            {showTrace ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          {showTrace && (
            <div className="mt-2 space-y-1.5 max-h-48 overflow-y-auto p-2 rounded-lg bg-surface-muted/40 border border-surface-border text-xs font-mono">
              {trace.map((step, idx) => (
                <div key={idx} className="flex items-start gap-2 py-1 border-b border-surface-border/50 last:border-b-0">
                  <span className="text-ink-muted shrink-0">#{idx + 1}</span>
                  <span className="text-accent-blue font-semibold">{step.agent || 'agent'}</span>
                  <span className="text-ink-muted">→</span>
                  <span className="text-ink-secondary">{step.action || 'action'}</span>
                  {step.target && (
                    <span className="text-accent-peach">({step.target})</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
