import { Link } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Mic, Database, Brain, Sparkles, CheckCircle2, AlertCircle } from 'lucide-react';

export default function GetStartedPage() {
  const steps = [
    {
      step: '01',
      title: 'Voice Capture & Transcript Streaming',
      badge: 'Hardware / Integration Required',
      badgeColor: 'bg-amber-50 text-amber-800 border-amber-200',
      icon: <Mic size={18} className="text-accent-blue" />,
      description:
        'MEMORA processes spoken transcripts captured via an Omi wearable device or the Omi developer webhook integration. Conversations are delivered in real time to the backend webhook endpoint.',
      details: [
        'Requires an Omi device paired with the Omi mobile application or simulator.',
        'Webhook URL must be directed to your MEMORA backend (/omi/conversation).',
        'Hardware setup is not automatic — device configuration is needed for live mic audio.',
      ],
    },
    {
      step: '02',
      title: 'Local Embedding & Vector Storage',
      badge: 'Local-First Vector Store',
      badgeColor: 'bg-blue-50 text-blue-800 border-blue-200',
      icon: <Database size={18} className="text-accent-peach" />,
      description:
        'When conversations conclude, transcripts are converted into 384-dimensional dense vectors using FastEmbed (BAAI/bge-small-en-v1.5) running locally and stored in Qdrant.',
      details: [
        'Runs completely on your local device without external embedding API calls.',
        'Memories are indexed with timestamp, speaker context, and user partition metadata.',
        'Sub-millisecond semantic similarity search across conversation history.',
      ],
    },
    {
      step: '03',
      title: 'Lyzr Multi-Agent Reasoning',
      badge: 'Cloud Intelligence',
      badgeColor: 'bg-purple-50 text-purple-800 border-purple-200',
      icon: <Brain size={18} className="text-accent-blue" />,
      description:
        'When an explicit question or task is spoken (e.g., "What did I study yesterday?"), the system automatically performs cosine retrieval and invokes Lyzr multi-agent pipelines.',
      details: [
        'Manager agent coordinates specialized workers for fact synthesis and action planning.',
        'Grounded answers are returned and dispatched back to your Omi device via notifications.',
        'Sanitized execution traces are recorded and viewable in the audit log.',
      ],
    },
    {
      step: '04',
      title: 'Independent Dashboard Exploration',
      badge: 'Instant Access',
      badgeColor: 'bg-emerald-50 text-emerald-800 border-emerald-200',
      icon: <Sparkles size={18} className="text-emerald-600" />,
      description:
        'You do not need an active Omi device connected right now to explore MEMORA. The application dashboard provides immediate access to test the vector store and reasoning traces.',
      details: [
        'Browse and filter existing memories stored in the local Qdrant collection.',
        'Run live semantic similarity queries with natural language questions.',
        'Inspect recorded multi-agent execution steps and runtime environment health.',
      ],
    },
  ];

  return (
    <div className="min-h-screen bg-canvas text-ink-primary flex flex-col justify-between">
      {/* Top Navigation */}
      <header className="border-b border-surface-border bg-white/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="text-ink-primary font-semibold text-lg tracking-tight hover:opacity-80 transition-opacity"
            >
              Memora
            </Link>
            <span className="text-surface-border">/</span>
            <span className="text-xs font-medium text-ink-secondary bg-surface-muted px-2 py-0.5 rounded border border-surface-border">
              Getting Started
            </span>
          </div>

          <div className="flex items-center gap-3 sm:gap-4">
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 text-xs text-ink-secondary hover:text-ink-primary transition-colors py-1.5"
            >
              <ArrowLeft size={13} />
              <span className="hidden sm:inline">Marketing Site</span>
            </Link>
            <Link
              to="/app"
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-ink-primary text-canvas text-xs font-medium hover:bg-ink-secondary transition-colors duration-200"
            >
              <span>Open demo dashboard</span>
              <ArrowRight size={13} />
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-16 space-y-12">
        {/* Hero header */}
        <div className="text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-surface-border bg-white text-xs font-medium text-ink-secondary shadow-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-accent-blue inline-block" />
            System Architecture &amp; Onboarding
          </div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-ink-primary tracking-tightest leading-tight">
            How MEMORA Works
          </h1>
          <p className="text-base sm:text-lg text-ink-secondary max-w-2xl mx-auto leading-relaxed">
            MEMORA connects spoken conversation capture to local vector memory and cloud-powered multi-agent reasoning.
          </p>
        </div>

        {/* Integration requirement callout */}
        <div className="p-4 sm:p-5 rounded-xl border border-amber-200/80 bg-amber-50/60 text-ink-primary flex items-start gap-3.5">
          <AlertCircle size={18} className="text-amber-700 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h2 className="text-xs font-semibold text-amber-900 uppercase tracking-wider">
              Integration &amp; Hardware Notice
            </h2>
            <p className="text-xs text-amber-800 leading-relaxed">
              Live conversation capture requires an appropriately configured Omi wearable device or compatible audio streaming client delivering webhook payloads. Voice capture is <strong>not automated out-of-the-box</strong> without hardware configuration. However, you can explore the full vector store and reasoning interface independently using the demo dashboard below.
            </p>
          </div>
        </div>

        {/* Step-by-step Architecture Breakdown */}
        <div className="space-y-6">
          {steps.map((item) => (
            <div
              key={item.step}
              className="p-6 sm:p-7 rounded-2xl border border-surface-border bg-white shadow-card space-y-4 transition-all hover:border-surface-hover"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-3 border-b border-surface-border">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-surface-muted border border-surface-border flex items-center justify-center shrink-0">
                    {item.icon}
                  </div>
                  <div>
                    <span className="text-[10px] font-mono font-semibold text-ink-muted uppercase tracking-wider">
                      Step {item.step}
                    </span>
                    <h3 className="text-sm sm:text-base font-semibold text-ink-primary">
                      {item.title}
                    </h3>
                  </div>
                </div>
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium border shrink-0 ${item.badgeColor}`}
                >
                  {item.badge}
                </span>
              </div>

              <p className="text-xs sm:text-sm text-ink-secondary leading-relaxed">
                {item.description}
              </p>

              <ul className="space-y-2 pt-1">
                {item.details.map((detail, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-xs text-ink-muted leading-relaxed">
                    <CheckCircle2 size={13} className="text-accent-blue shrink-0 mt-0.5" />
                    <span>{detail}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Call to action card */}
        <div className="p-8 rounded-2xl border border-surface-border bg-white shadow-card text-center space-y-6">
          <div className="max-w-md mx-auto space-y-2">
            <h2 className="text-xl sm:text-2xl font-bold text-ink-primary tracking-tight">
              Ready to explore the dashboard?
            </h2>
            <p className="text-xs sm:text-sm text-ink-secondary leading-relaxed">
              Open the functional MEMORA console to test semantic vector search, inspect stored memories, and review reasoning runs.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              to="/app"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-ink-primary text-canvas text-sm font-semibold hover:bg-ink-secondary transition-colors duration-200 shadow-sm"
            >
              <span>Open demo dashboard</span>
              <ArrowRight size={15} />
            </Link>
            <Link
              to="/"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg border border-surface-border bg-white text-sm font-medium text-ink-secondary hover:text-ink-primary hover:border-surface-hover transition-colors duration-200"
            >
              <span>Back to marketing site</span>
            </Link>
          </div>

          <p className="text-[11px] text-ink-faint">
            Prototype demo identity: <span className="font-mono text-ink-secondary">default_user</span> · Local Qdrant embedded storage
          </p>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-surface-border py-6 bg-canvas text-center">
        <p className="text-[11px] text-ink-faint">
          MEMORA · Local vector storage · Cloud-powered reasoning
        </p>
      </footer>
    </div>
  );
}
