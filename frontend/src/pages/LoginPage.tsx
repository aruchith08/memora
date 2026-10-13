import { Link } from 'react-router-dom';
import { Shield, ArrowRight, ArrowLeft, Info, Cpu } from 'lucide-react';

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-canvas text-ink-primary flex flex-col justify-between">
      {/* Top minimal header */}
      <header className="border-b border-surface-border bg-white/80 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link
            to="/"
            className="text-ink-primary font-semibold text-lg tracking-tight hover:opacity-80 transition-opacity"
          >
            Memora
          </Link>
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-xs text-ink-secondary hover:text-ink-primary transition-colors py-1.5"
          >
            <ArrowLeft size={13} />
            Back to homepage
          </Link>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex items-center justify-center px-4 sm:px-6 py-12">
        <div className="w-full max-w-md">
          {/* Card */}
          <div className="p-6 sm:p-8 rounded-2xl border border-surface-border bg-white shadow-card space-y-6">
            {/* Header */}
            <div className="text-center space-y-2">
              <div className="w-12 h-12 mx-auto rounded-xl bg-accent-blue/10 border border-accent-blue/20 flex items-center justify-center text-accent-blue mb-4">
                <Shield size={24} />
              </div>
              <h1 className="text-xl sm:text-2xl font-bold text-ink-primary tracking-tight">
                Sign in to MEMORA
              </h1>
              <p className="text-xs text-ink-secondary">
                Personal Memory &amp; Multi-Agent Intelligence System
              </p>
            </div>

            {/* Status notice box */}
            <div className="p-4 rounded-xl border border-surface-border bg-surface-muted/40 space-y-2.5">
              <div className="flex items-center gap-2 text-xs font-semibold text-ink-primary">
                <Info size={14} className="text-accent-blue shrink-0" />
                <span>Demo Tenant Workspace</span>
              </div>
              <p className="text-xs text-ink-secondary leading-relaxed">
                Direct session enabled. Voice memories are partitioned by user identifier and stored in a configured Qdrant collection with server-side payload filtering.
              </p>
              <div className="pt-2 border-t border-surface-border/60 text-[11px] text-ink-muted leading-relaxed">
                Queries are scoped to your active user identifier, ensuring isolated memory retrieval and observable Lyzr multi-agent analysis.
              </div>
            </div>

            {/* Actions */}
            <div className="space-y-3 pt-2">
              <Link
                to="/app"
                className="w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-ink-primary text-canvas text-sm font-semibold hover:bg-ink-secondary transition-colors duration-200 shadow-sm"
              >
                <span>Enter MEMORA Console</span>
                <ArrowRight size={15} />
              </Link>

              <Link
                to="/get-started"
                className="w-full inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg border border-surface-border bg-white text-xs font-medium text-ink-secondary hover:text-ink-primary hover:border-surface-hover transition-colors duration-200"
              >
                <Cpu size={14} />
                <span>Architecture &amp; Onboarding</span>
              </Link>
            </div>

            {/* Disclaimer */}
            <p className="text-[11px] text-center text-ink-faint leading-normal">
              Continuous Ambient Intelligence · Sovereign Vector Isolation
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-surface-border py-4 bg-canvas text-center">
        <p className="text-[11px] text-ink-faint">
          MEMORA · Qdrant Cloud Vector Storage · Lyzr Multi-Agent Reasoning
        </p>
      </footer>
    </div>
  );
}
