import { HardDrive, Eye, Lock } from 'lucide-react';

const pillars = [
  {
    icon: <HardDrive size={20} strokeWidth={1.5} className="text-ink-secondary" />,
    title: 'Local vector storage',
    description:
      'Memories and vector embeddings are stored in a local Qdrant instance on your machine. When you ask questions, relevant memory context may be sent to Lyzr for cloud-based multi-agent reasoning.',
  },
  {
    icon: <Eye size={20} strokeWidth={1.5} className="text-ink-secondary" />,
    title: 'No product analytics',
    description:
      'Memora contains no behavioral trackers, marketing analytics, or advertising telemetry. External network activity is limited to configured operational services such as AI reasoning and notifications.',
  },
  {
    icon: <Lock size={20} strokeWidth={1.5} className="text-ink-secondary" />,
    title: 'UID-isolated memories',
    description:
      'Memories are partitioned by user identifier with server-side query filters to avoid cross-user retrieval. This provides prototype isolation and does not represent an enterprise security certification.',
  },
];

export default function PrivacyTrust() {
  return (
    <section id="privacy" className="py-20 lg:py-28 border-t border-surface-border">
      <div className="max-w-6xl mx-auto px-6 lg:px-8">
        <div className="max-w-xl mb-14">
          <p className="text-xs font-semibold text-ink-secondary uppercase tracking-widest mb-4">
            Privacy
          </p>
          <h2 className="text-3xl lg:text-4xl font-bold text-ink-primary leading-tight tracking-tighter text-balance">
            Your data. Your device. Your control.
          </h2>
          <p className="mt-4 text-base text-ink-secondary leading-relaxed">
            Memora is designed to keep sensitive personal context private. Here is exactly what that means in practice.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {pillars.map((pillar) => (
            <div key={pillar.title} className="flex flex-col gap-4">
              <div className="w-10 h-10 rounded-xl border border-surface-border bg-white flex items-center justify-center shadow-sm">
                {pillar.icon}
              </div>
              <div>
                <h3 className="text-sm font-semibold text-ink-primary mb-1.5">{pillar.title}</h3>
                <p className="text-sm text-ink-secondary leading-relaxed">{pillar.description}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Honest disclaimer */}
        <div className="mt-12 p-4 rounded-xl border border-surface-border bg-surface-muted/60">
          <p className="text-xs text-ink-muted leading-relaxed">
            <span className="font-semibold text-ink-secondary">Note:</span> Memora is an open-source personal project, not a commercial product with enterprise security certifications. Treat it accordingly. Do not store sensitive credentials, medical records, or financial data in your Memora instance without understanding the full system architecture.
          </p>
        </div>
      </div>
    </section>
  );
}
