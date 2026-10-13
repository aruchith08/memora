import { Link } from 'react-router-dom';

export default function FinalCTA() {
  return (
    <section className="py-20 lg:py-28 border-t border-surface-border">
      <div className="max-w-6xl mx-auto px-6 lg:px-8">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl lg:text-5xl font-bold text-ink-primary leading-tight tracking-tightest text-balance">
            Never lose a thought again.
          </h2>
          <p className="mt-5 text-base lg:text-lg text-ink-secondary leading-relaxed text-balance">
            Memora runs locally, speaks Omi, and thinks with Lyzr. Set it up once and it quietly works in the background — capturing, remembering, acting.
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <Link
              to="/app"
              className="inline-flex items-center px-7 py-3.5 rounded-lg bg-ink-primary text-canvas text-sm font-semibold hover:bg-ink-secondary transition-colors duration-200 shadow-sm"
            >
              Open MEMORA
            </Link>
            <Link
              to="/get-started"
              className="inline-flex items-center px-7 py-3.5 rounded-lg border border-surface-border bg-white text-sm font-medium text-ink-secondary hover:text-ink-primary hover:border-surface-hover transition-colors duration-200"
            >
              Get started
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
