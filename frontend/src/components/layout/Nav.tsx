import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import { cn } from '../../lib/utils';

const navLinks = [
  { label: 'Product', href: '#product' },
  { label: 'How it works', href: '#how-it-works' },
  { label: 'Privacy', href: '#privacy' },
];

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const isHome = location.pathname === '/';

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [location]);

  const handleAnchor = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    if (isHome && href.startsWith('#')) {
      e.preventDefault();
      document.querySelector(href)?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <header
      className={cn(
        'fixed top-0 inset-x-0 z-50 transition-all duration-300',
        scrolled
          ? 'bg-canvas/95 backdrop-blur-sm border-b border-surface-border shadow-sm'
          : 'bg-transparent'
      )}
    >
      <div className="max-w-6xl mx-auto px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Wordmark */}
        <Link
          to="/"
          className="text-ink-primary font-semibold text-lg tracking-tight select-none"
        >
          Memora
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-8">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={isHome ? link.href : `/${link.href}`}
              onClick={(e) => handleAnchor(e, link.href)}
              className="text-sm text-ink-secondary hover:text-ink-primary transition-colors duration-200"
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* Desktop CTA */}
        <div className="hidden md:flex items-center gap-3">
          <Link
            to="/login"
            className="text-sm text-ink-secondary hover:text-ink-primary transition-colors duration-200"
          >
            Sign in
          </Link>
          <Link
            to="/get-started"
            className="inline-flex items-center px-4 py-2 rounded-md bg-ink-primary text-canvas text-sm font-medium hover:bg-ink-secondary transition-colors duration-200"
          >
            Get started
          </Link>
        </div>

        {/* Mobile menu toggle */}
        <button
          className="md:hidden p-2 -mr-2 text-ink-secondary hover:text-ink-primary transition-colors"
          onClick={() => setMobileOpen((v) => !v)}
          aria-label="Toggle navigation"
        >
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="md:hidden bg-canvas border-b border-surface-border px-6 py-5 flex flex-col gap-4">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={isHome ? link.href : `/${link.href}`}
              onClick={(e) => { handleAnchor(e, link.href); setMobileOpen(false); }}
              className="text-sm text-ink-secondary hover:text-ink-primary transition-colors"
            >
              {link.label}
            </a>
          ))}
          <div className="pt-2 border-t border-surface-border flex flex-col gap-3">
            <Link to="/login" className="text-sm text-ink-secondary hover:text-ink-primary transition-colors">
              Sign in
            </Link>
            <Link
              to="/get-started"
              className="inline-flex justify-center items-center px-4 py-2.5 rounded-md bg-ink-primary text-canvas text-sm font-medium"
            >
              Get started
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
