import { cn } from '../../lib/utils';
import { Mic, Database, Layers, Brain, Zap, FileText } from 'lucide-react';

const agents = [
  {
    id: 'manager',
    name: 'Manager',
    role: 'Orchestration',
    description:
      'Receives the incoming question and retrieved memory context. Delegates sub-tasks to Reasoner and Action Planner, then synthesises the final response.',
    accent: 'blue',
    connections: ['reasoner', 'planner'],
  },
  {
    id: 'reasoner',
    name: 'Reasoner',
    role: 'Analysis',
    description:
      'Analyses retrieved memories for relevance, resolves contradictions, and extracts the key facts needed to answer the question accurately.',
    accent: 'peach',
    connections: [],
  },
  {
    id: 'planner',
    name: 'Action Planner',
    role: 'Execution',
    description:
      'Determines what follow-up actions are appropriate — calendar entries, reminders, notifications — and queues them for delivery.',
    accent: 'blue',
    connections: [],
  },
];

const accentMap: Record<string, { border: string; badge: string; dot: string }> = {
  blue: {
    border: 'border-accent-blue/30',
    badge: 'bg-accent-blue/10 text-accent-blue',
    dot: 'bg-accent-blue',
  },
  peach: {
    border: 'border-accent-peach/30',
    badge: 'bg-accent-peach/20 text-accent-peach',
    dot: 'bg-accent-peach',
  },
};

// Flowchart matching reference image: Omi event -> Qdrant retrieval -> Manager -> (Reasoner / Action Planner) -> Response + actions
function PipelineDiagram() {
  const steps = [
    { icon: <Mic size={14} strokeWidth={2} />, label: 'Omi event', color: 'bg-blue-50 text-blue-600' },
    { icon: <Database size={14} strokeWidth={2} />, label: 'Qdrant retrieval', color: 'bg-surface-muted text-ink-muted' },
    { icon: <Layers size={13} strokeWidth={2} />, label: 'Manager', color: 'bg-blue-600 text-white', highlight: true },
  ];

  return (
    <div className="w-full mb-12 py-4">
      {/* Mobile: vertical stack */}
      <div className="md:hidden flex flex-col items-center gap-1">
        {steps.map((step, i) => (
          <div key={i} className="flex flex-col items-center gap-1">
            <div className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border ${step.highlight ? 'border-blue-200 bg-blue-50/70 font-semibold' : 'border-surface-border bg-white'} text-xs font-medium text-ink-primary shadow-xs w-48 justify-center`}>
              <div className={`w-6 h-6 rounded-full ${step.color} flex items-center justify-center shrink-0`}>
                {step.icon}
              </div>
              <span>{step.label}</span>
            </div>
            {i < steps.length - 1 && (
              <svg width="12" height="16" viewBox="0 0 12 16" fill="none" className="text-surface-border">
                <path d="M6 0V12M6 12L2 8M6 12L10 8" stroke="#D1D5DB" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            )}
          </div>
        ))}
        {/* Fork to workers */}
        <div className="flex flex-col items-center gap-1 mt-1">
          <svg width="12" height="16" viewBox="0 0 12 16" fill="none">
            <path d="M6 0V12M6 12L2 8M6 12L10 8" stroke="#D1D5DB" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <div className="flex gap-3">
            <div className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-orange-200/90 bg-[#FFF7ED] text-xs font-semibold text-ink-primary shadow-xs">
              <div className="w-5 h-5 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center shrink-0">
                <Brain size={12} strokeWidth={2} />
              </div>
              <span>Reasoner</span>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-blue-200/90 bg-[#EFF6FF] text-xs font-semibold text-ink-primary shadow-xs">
              <div className="w-5 h-5 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shrink-0">
                <Zap size={12} strokeWidth={2} />
              </div>
              <span>Planner</span>
            </div>
          </div>
          <svg width="12" height="16" viewBox="0 0 12 16" fill="none">
            <path d="M6 0V12M6 12L2 8M6 12L10 8" stroke="#D1D5DB" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <div className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl border border-surface-border bg-white text-xs font-medium text-ink-primary shadow-xs">
            <div className="w-6 h-6 rounded-full bg-surface-muted text-ink-secondary flex items-center justify-center shrink-0">
              <FileText size={14} strokeWidth={1.8} />
            </div>
            <span>Response + actions</span>
          </div>
        </div>
      </div>

      {/* Desktop: horizontal scroll */}
      <div className="hidden md:block overflow-x-auto py-6 scrollbar-none">
        <div className="min-w-[760px] max-w-4xl mx-auto flex items-center justify-center gap-2">
          {/* Step 1: Omi event */}
          <div className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl border border-surface-border bg-white text-xs font-medium text-ink-primary shadow-xs">
            <div className="w-6 h-6 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
              <Mic size={14} strokeWidth={2} />
            </div>
            <span className="whitespace-nowrap">Omi event</span>
          </div>

          {/* Straight arrow */}
          <div className="text-surface-border shrink-0 px-0.5">
            <svg width="24" height="12" viewBox="0 0 24 12" fill="none">
              <path d="M0 6H20M20 6L15 1M20 6L15 11" stroke="#D1D5DB" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>

          {/* Step 2: Qdrant retrieval */}
          <div className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl border border-surface-border bg-white text-xs font-medium text-ink-primary shadow-xs">
            <div className="w-6 h-6 rounded-full bg-surface-muted text-ink-muted flex items-center justify-center shrink-0">
              <Database size={14} strokeWidth={2} />
            </div>
            <span className="whitespace-nowrap">Qdrant retrieval</span>
          </div>

          {/* Straight arrow */}
          <div className="text-surface-border shrink-0 px-0.5">
            <svg width="24" height="12" viewBox="0 0 24 12" fill="none">
              <path d="M0 6H20M20 6L15 1M20 6L15 11" stroke="#D1D5DB" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>

          {/* Step 3: Manager */}
          <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-blue-200 bg-blue-50/70 text-xs font-semibold text-ink-primary shadow-xs">
            <div className="w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-2xs">
              <Layers size={13} strokeWidth={2} />
            </div>
            <span className="whitespace-nowrap">Manager</span>
          </div>

          {/* Fork Connector curve */}
          <div className="shrink-0 text-surface-border w-6 flex items-center justify-center">
            <svg width="24" height="68" viewBox="0 0 24 68" fill="none">
              <path d="M0 34C12 34 12 14 22 14" stroke="#D1D5DB" strokeWidth="1.5" strokeLinecap="round"/>
              <path d="M19 11L23 14L19 17" stroke="#D1D5DB" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M0 34C12 34 12 54 22 54" stroke="#D1D5DB" strokeWidth="1.5" strokeLinecap="round"/>
              <path d="M19 51L23 54L19 57" stroke="#D1D5DB" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>

          {/* Stacked workers: Reasoner and Action Planner */}
          <div className="flex flex-col gap-2.5 shrink-0">
            <div className="flex items-center gap-2 px-4 py-2 rounded-xl border border-orange-200/90 bg-[#FFF7ED] text-xs font-semibold text-ink-primary shadow-xs min-w-[150px]">
              <div className="w-5 h-5 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center shrink-0">
                <Brain size={12} strokeWidth={2} />
              </div>
              <span>Reasoner</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 rounded-xl border border-blue-200/90 bg-[#EFF6FF] text-xs font-semibold text-ink-primary shadow-xs min-w-[150px]">
              <div className="w-5 h-5 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shrink-0">
                <Zap size={12} strokeWidth={2} />
              </div>
              <span>Action Planner</span>
            </div>
          </div>

          {/* Join Connector curve */}
          <div className="shrink-0 text-surface-border w-6 flex items-center justify-center">
            <svg width="24" height="68" viewBox="0 0 24 68" fill="none">
              <path d="M0 14C10 14 10 34 22 34" stroke="#D1D5DB" strokeWidth="1.5" strokeLinecap="round"/>
              <path d="M0 54C10 54 10 34 22 34" stroke="#D1D5DB" strokeWidth="1.5" strokeLinecap="round"/>
              <path d="M19 31L23 34L19 37" stroke="#D1D5DB" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>

          {/* Step 5: Response + actions */}
          <div className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl border border-surface-border bg-white text-xs font-medium text-ink-primary shadow-xs">
            <div className="w-6 h-6 rounded-full bg-surface-muted text-ink-secondary flex items-center justify-center shrink-0">
              <FileText size={14} strokeWidth={1.8} />
            </div>
            <span className="whitespace-nowrap">Response + actions</span>
          </div>
        </div>
      </div>
    </div>
  );
}


export default function MultiAgentSection() {
  return (
    <section id="product" className="py-20 lg:py-28 bg-surface-muted/40 border-t border-surface-border">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-xl mb-14">
          <p className="text-xs font-semibold text-accent-peach uppercase tracking-widest mb-4">
            Multi-agent orchestration
          </p>
          <h2 className="text-3xl lg:text-4xl font-bold text-ink-primary leading-tight tracking-tighter text-balance">
            Three agents. One coherent answer.
          </h2>
          <p className="mt-4 text-base text-ink-secondary leading-relaxed">
            Lyzr orchestrates a purpose-built agent team that divides the reasoning work so every response is both accurate and actionable.
          </p>
        </div>

        <PipelineDiagram />

        <div className="grid md:grid-cols-3 gap-6">
          {agents.map((agent) => {
            const colors = accentMap[agent.accent];
            return (
              <div
                key={agent.id}
                className={cn(
                  'rounded-2xl border bg-white p-6 shadow-card hover:shadow-floating transition-shadow duration-300',
                  colors.border
                )}
              >
                <div className="flex items-center gap-2 mb-4">
                  <span className={cn('w-2 h-2 rounded-full flex-shrink-0', colors.dot)} />
                  <span className={cn('text-[10px] font-semibold px-2 py-0.5 rounded-full', colors.badge)}>
                    {agent.role}
                  </span>
                </div>
                <h3 className="text-base font-semibold text-ink-primary mb-2">{agent.name}</h3>
                <p className="text-sm text-ink-secondary leading-relaxed">{agent.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
