import { HardDrive, Eye, Lock } from 'lucide-react';

const pillars = [
  {
    icon: <HardDrive size={20} strokeWidth={1.5} className="text-ink-secondary" />,
    title: 'Cloud vector storage',
    description:
      'Memories and vector embeddings are indexed in dedicated Qdrant Cloud clusters with sub-second retrieval latency. Relevant context is routed to Lyzr for multi-agent reasoning.',
  },
  {
    icon: <Eye size={20} strokeWidth={1.5} className="text-ink-secondary" />,
    title: 'Zero behavioral tracking',
    description:
      'Memora contains no behavioral trackers, third-party analytics, or advertising telemetry. External network activity is limited strictly to operational AI reasoning and wearable notifications.',
  },
  {
    icon: <Lock size={20} strokeWidth={1.5} className="text-ink-secondary" />,
    title: 'Cryptographic tenant isolation',
    description:
      'Memories are partitioned by unique user credentials with server-side HNSW filtering, guaranteeing complete tenant isolation and zero cross-user vector retrieval.',
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

        {/* Security policy */}
        <div className="mt-12 p-4 rounded-xl border border-surface-border bg-surface-muted/60">
          <p className="text-xs text-ink-muted leading-relaxed">
            <span className="font-semibold text-ink-secondary">Sovereign Architecture:</span> MEMORA enforces zero-knowledge ambient retention policies. All vector payloads are scoped to the active tenant ID with instant permanent deletion (right to forget) enforced directly at the vector database layer.
          </p>
        </div>
      </div>
    </section>
  );
}
