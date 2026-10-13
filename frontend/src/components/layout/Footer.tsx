import { Link } from 'react-router-dom';

const footerLinks = {
  Product: [
    { label: 'How it works', href: '#how-it-works' },
    { label: 'Privacy', href: '#privacy' },
    { label: 'Open app', href: '/app' },
  ],
  Resources: [
    { label: 'Documentation', href: '#' },
    { label: 'GitHub', href: '#' },
    { label: 'Changelog', href: '#' },
  ],
};

export default function Footer() {
  return (
    <footer className="border-t border-surface-border bg-canvas">
      <div className="max-w-6xl mx-auto px-6 lg:px-8 py-14 lg:py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-10">
          {/* Brand column */}
          <div className="col-span-2">
            <Link to="/" className="text-ink-primary font-semibold text-base tracking-tight">
              Memora
            </Link>
            <p className="mt-3 text-sm text-ink-muted leading-relaxed max-w-xs">
              Voice-powered personal memory and action assistant. Built with Omi, FastAPI, Qdrant, and Lyzr multi-agent orchestration.
            </p>
          </div>

          {/* Link columns */}
          {Object.entries(footerLinks).map(([group, links]) => (
            <div key={group}>
              <p className="text-xs font-semibold text-ink-primary uppercase tracking-widest mb-4">
                {group}
              </p>
              <ul className="space-y-3">
                {links.map((link) => (
                  <li key={link.label}>
                    {link.href.startsWith('/') || link.href.startsWith('#') ? (
                      <a
                        href={link.href}
                        className="text-sm text-ink-muted hover:text-ink-primary transition-colors duration-200"
                      >
                        {link.label}
                      </a>
                    ) : (
                      <a
                        href={link.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-ink-muted hover:text-ink-primary transition-colors duration-200"
                      >
                        {link.label}
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 pt-8 border-t border-surface-border flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-ink-faint">
            &copy; {new Date().getFullYear()} Memora. All rights reserved.
          </p>
          <p className="text-xs text-ink-faint">
            Local vector storage · Cloud-powered reasoning
          </p>
        </div>
      </div>
    </footer>
  );
}
