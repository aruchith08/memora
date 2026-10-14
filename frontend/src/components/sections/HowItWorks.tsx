import { Mic, Database, Network } from 'lucide-react';

const steps = [
  {
    number: '01',
    icon: <Mic size={22} strokeWidth={1.5} className="text-accent-blue" />,
    title: 'Capture',
    description:
      'Speak to your Omi device. Omi delivers conversation transcripts to Memora via webhook, and Memora generates semantic embeddings locally into your personal vector store.',
  },
  {
    number: '02',
    icon: <Database size={22} strokeWidth={1.5} className="text-accent-peach" />,
    title: 'Remember',
    description:
      'Memories are stored in Qdrant with semantic embeddings. When you ask a question, relevant context surfaces instantly — no keyword search, no scrolling through history.',
  },
  {
    number: '03',
    icon: <Network size={22} strokeWidth={1.5} className="text-accent-blue" />,
    title: 'Reason and act',
    description:
      'A Lyzr multi-agent pipeline — Manager, Reasoner, and Action Planner — synthesises retrieved memories into a clear answer and queues the right follow-up actions.',
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="py-20 lg:py-28 border-t border-surface-border">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-xl mb-14">
          <p className="text-xs font-semibold text-accent-blue uppercase tracking-widest mb-4">
            How it works
          </p>
          <h2 className="text-3xl lg:text-4xl font-bold text-ink-primary leading-tight tracking-tighter text-balance">
            From voice to action in three steps
          </h2>
          <p className="mt-4 text-base text-ink-secondary leading-relaxed">
            Memora handles the full loop — capture, retrieval, reasoning — so you never lose context on anything you've said.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {steps.map((step) => (
            <div key={step.number} className="group">
              <div className="flex items-center gap-3 mb-5">
                <span className="text-xs font-mono text-ink-faint">{step.number}</span>
                <div className="w-10 h-10 rounded-xl border border-surface-border bg-white flex items-center justify-center shadow-sm group-hover:shadow-card transition-shadow duration-300">
                  {step.icon}
                </div>
              </div>
              <h3 className="text-base font-semibold text-ink-primary mb-2">{step.title}</h3>
              <p className="text-sm text-ink-secondary leading-relaxed">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
