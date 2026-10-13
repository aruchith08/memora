import { Link } from 'react-router-dom';
import { Mic, ChevronLeft } from 'lucide-react';

export default function AppPlaceholder() {
  return (
    <div className="min-h-screen bg-canvas flex flex-col">
      {/* Minimal header */}
      <header className="h-14 border-b border-surface-border flex items-center px-6 justify-between">
        <Link to="/" className="text-ink-primary font-semibold text-base tracking-tight">
          Memora
        </Link>
        <Link
          to="/"
          className="flex items-center gap-1.5 text-xs text-ink-muted hover:text-ink-primary transition-colors"
        >
          <ChevronLeft size={14} />
          Back to site
        </Link>
      </header>

      {/* Centred placeholder */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 text-center">
        <div className="w-16 h-16 rounded-2xl border border-surface-border bg-white shadow-card flex items-center justify-center mb-8">
          <Mic size={28} strokeWidth={1.25} className="text-ink-secondary" />
        </div>

        <h1 className="text-2xl lg:text-3xl font-bold text-ink-primary tracking-tighter mb-3">
          The app is coming.
        </h1>
        <p className="text-sm text-ink-secondary max-w-xs leading-relaxed mb-8">
          The Memora dashboard — memory browser, search, and live reasoning trace — is being built. Check back soon.
        </p>

        <div className="flex flex-col sm:flex-row gap-3">
          <a
            href="http://127.0.0.1:8000/health"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center px-5 py-2.5 rounded-lg border border-surface-border bg-white text-xs font-medium text-ink-secondary hover:text-ink-primary hover:border-surface-hover transition-colors duration-200"
          >
            Backend health check
          </a>
          <a
            href="http://127.0.0.1:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center px-5 py-2.5 rounded-lg border border-surface-border bg-white text-xs font-medium text-ink-secondary hover:text-ink-primary hover:border-surface-hover transition-colors duration-200"
          >
            API docs (FastAPI)
          </a>
        </div>
      </main>

      <footer className="h-12 border-t border-surface-border flex items-center justify-center">
        <p className="text-xs text-ink-faint">Memora — Stage 2 coming soon</p>
      </footer>
    </div>
  );
}
