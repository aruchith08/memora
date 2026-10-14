import { Link } from 'react-router-dom';
import { Mic, Brain, Zap, Check, Layers } from 'lucide-react';

// Product preview showcasing MEMORA live audio ingestion, vector indexing and action pipeline
function ProductPreviewCard() {
  const waveHeights = [20, 32, 16, 42, 60, 35, 75, 45, 90, 65, 80, 50, 68, 30, 48, 22];

  return (
    <div className="relative w-full max-w-[460px] mx-auto rounded-2xl border border-surface-border/80 bg-white shadow-preview overflow-hidden transition-all duration-300 ease-out hover:shadow-floating cursor-default">
      {/* Window chrome header */}
      <div className="flex items-center justify-between px-3.5 sm:px-4 py-2.5 sm:py-3 border-b border-surface-border/60 bg-white">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#EF4444]" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#F59E0B]" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#10B981]" />
          <span className="ml-2 text-[10px] sm:text-[11px] text-ink-muted/80 font-mono tracking-tight">
            memora · live pipeline
          </span>
        </div>
        <div className="flex items-center gap-1 text-[10px] sm:text-[11px] font-semibold text-ink-primary">
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500" />
          </span>
          <span className="text-[10px] sm:text-[11px] font-medium text-ink-primary">Live</span>
        </div>
      </div>

      {/* Pipeline steps container */}
      <div className="p-2.5 sm:p-3.5 space-y-2 sm:space-y-2.5 bg-[#FAF9F6]/60">
        {/* Step 1: Voice captured */}
        <div className="flex items-center justify-between p-2 sm:p-2.5 rounded-xl bg-[#F6F5F2] border border-surface-border/50 transition-all hover:border-surface-border gap-2">
          <div className="flex items-center gap-2 sm:gap-2.5 min-w-0 flex-1">
            <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-white border border-surface-border/70 flex items-center justify-center shrink-0 shadow-xs">
              <Mic size={14} strokeWidth={2} className="text-[#2563EB]" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1 sm:gap-1.5 flex-wrap">
                <span className="text-[11px] sm:text-xs font-bold text-ink-primary">Voice captured</span>
                <span className="text-[9px] sm:text-[10px] font-semibold px-1.5 py-0.2 rounded-full bg-[#E0E7FF] text-[#3B82F6]">
                  done
                </span>
              </div>
              <p className="text-[10px] sm:text-[11px] text-ink-muted leading-tight truncate">
                "Remind me about the investor meeting on Friday."
              </p>
            </div>
          </div>

          {/* Animated audio wave */}
          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0 pl-1">
            <div className="flex items-center gap-0.5 h-4 sm:h-5">
              {waveHeights.slice(0, 10).map((h, idx) => (
                <span
                  key={idx}
                  className="w-[2px] rounded-full bg-[#3B82F6] animate-wave-bar"
                  style={{
                    height: `${h}%`,
                    animationDelay: `${(idx * 0.08) % 1.2}s`,
                    animationDuration: '1.2s',
                  }}
                />
              ))}
            </div>
            <span className="text-[9px] sm:text-[10px] font-mono text-ink-muted tracking-tight">0:04</span>
          </div>
        </div>

        {/* Step 2: Memory stored */}
        <div className="flex items-center justify-between p-2 sm:p-2.5 rounded-xl bg-[#F6F5F2] border border-surface-border/50 transition-all hover:border-surface-border gap-2">
          <div className="flex items-center gap-2 sm:gap-2.5 min-w-0 flex-1">
            <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-white border border-surface-border/70 flex items-center justify-center shrink-0 shadow-xs">
              <Brain size={14} strokeWidth={2} className="text-[#EA580C]" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1 sm:gap-1.5 flex-wrap">
                <span className="text-[11px] sm:text-xs font-bold text-ink-primary">Memory stored</span>
                <span className="text-[9px] sm:text-[10px] font-semibold px-1.5 py-0.2 rounded-full bg-[#E0E7FF] text-[#3B82F6]">
                  done
                </span>
              </div>
              <p className="text-[10px] sm:text-[11px] text-ink-muted leading-tight truncate font-mono">
                Qdrant Cloud · bge-small-en-v1.5
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1 px-2 sm:px-2.5 py-0.5 sm:py-1 rounded-full bg-white/90 border border-surface-border/70 text-[9px] sm:text-[10px] font-medium text-ink-secondary shrink-0 shadow-xs">
            <Check size={11} strokeWidth={2.5} className="text-emerald-500" />
            <span>426 ms</span>
          </div>
        </div>

        {/* Step 3: Action surfaced */}
        <div className="flex items-center justify-between p-2 sm:p-2.5 rounded-xl bg-[#EFF6FF] border border-[#BFDBFE] transition-all shadow-xs gap-2">
          <div className="flex items-center gap-2 sm:gap-2.5 min-w-0 flex-1">
            <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-white border border-[#BFDBFE] flex items-center justify-center shrink-0 shadow-xs">
              <Zap size={14} strokeWidth={2} className="text-[#2563EB]" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1 sm:gap-1.5 flex-wrap">
                <span className="text-[11px] sm:text-xs font-bold text-ink-primary">Action surfaced</span>
                <span className="text-[9px] sm:text-[10px] font-semibold px-1.5 py-0.2 rounded-full bg-[#FFEDD5] text-[#EA580C]">
                  processing
                </span>
              </div>
              <p className="text-[10px] sm:text-[11px] text-ink-muted leading-tight truncate">
                Calendar block created · Reminder set
              </p>
            </div>
          </div>

          {/* Animated Spinner ring */}
          <div className="relative w-4 h-4 sm:w-5 sm:h-5 shrink-0 flex items-center justify-center">
            <div className="w-3.5 h-3.5 sm:w-4 sm:h-4 rounded-full border-2 border-blue-200 border-t-[#2563EB] animate-spin" />
          </div>
        </div>

        {/* Multi-Agent status tabs row */}
        <div className="pt-1 grid grid-cols-3 gap-1 sm:gap-1.5">
          {/* Manager active card */}
          <div className="flex items-center justify-center gap-1 sm:gap-1.5 py-1.5 px-1 sm:px-2 rounded-lg bg-white border border-surface-border shadow-xs text-center">
            <Layers size={12} strokeWidth={1.8} className="text-ink-primary shrink-0" />
            <span className="text-[10px] sm:text-[11px] font-semibold text-ink-primary truncate">Manager</span>
          </div>

          {/* Reasoner */}
          <div className="flex items-center justify-center gap-1 sm:gap-1.5 py-1.5 px-1 sm:px-2 rounded-lg bg-transparent border border-transparent hover:bg-white/60 transition-colors text-center">
            <Brain size={12} strokeWidth={1.8} className="text-ink-primary shrink-0" />
            <span className="text-[10px] sm:text-[11px] font-medium text-ink-primary truncate">Reasoner</span>
          </div>

          {/* Action Planner */}
          <div className="flex items-center justify-center gap-1 sm:gap-1.5 py-1.5 px-1 sm:px-2 rounded-lg bg-transparent border border-transparent hover:bg-white/60 transition-colors text-center">
            <Zap size={12} strokeWidth={1.8} className="text-ink-primary shrink-0" />
            <span className="text-[10px] sm:text-[11px] font-medium text-ink-primary truncate">Planner</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Hero() {
  return (
    <section className="relative pt-28 pb-16 lg:pt-40 lg:pb-28 overflow-hidden">
      {/* Subtle radial backdrop */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          background:
            'radial-gradient(ellipse 70% 50% at 50% -10%, rgba(186,205,234,0.18) 0%, transparent 70%)',
        }}
      />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-10 lg:gap-16 items-center">
          {/* Left: copy */}
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-surface-border bg-white text-xs text-ink-secondary mb-6 sm:mb-8 shadow-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-accent-blue inline-block" />
              Powered by Lyzr multi-agent orchestration
            </div>

            <h1 className="text-3xl sm:text-5xl lg:text-6xl font-bold text-ink-primary leading-[1.08] tracking-tightest text-balance">
              Your memory.{' '}
              <span className="text-ink-secondary">Working for you.</span>
            </h1>

            <p className="mt-5 sm:mt-6 text-base sm:text-lg text-ink-secondary leading-relaxed max-w-md text-balance">
              Speak naturally. Memora captures, understands, and acts — surfacing the right context exactly when you need it.
            </p>

            <div className="mt-7 sm:mt-9 flex flex-col xs:flex-row flex-wrap gap-3">
              <Link
                to="/app"
                className="inline-flex items-center justify-center px-6 py-3 rounded-lg bg-ink-primary text-canvas text-sm font-semibold hover:bg-ink-secondary transition-colors duration-200 shadow-sm"
              >
                Open MEMORA
              </Link>
              <Link
                to="/get-started"
                className="inline-flex items-center justify-center px-6 py-3 rounded-lg border border-surface-border bg-white text-sm font-medium text-ink-secondary hover:text-ink-primary hover:border-surface-hover transition-colors duration-200"
              >
                Get started
              </Link>
            </div>

            <p className="mt-6 text-xs text-ink-faint">
              No account required for local use. Requires Omi device for voice capture.
            </p>
          </div>

          {/* Right: product preview */}
          <div className="flex justify-center lg:justify-end">
            <ProductPreviewCard />
          </div>
        </div>
      </div>
    </section>
  );
}
