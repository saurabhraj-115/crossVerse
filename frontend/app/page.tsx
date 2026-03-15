import Link from 'next/link';
import { BookOpen, Scale, Swords, Compass, ArrowRight, Sparkles } from 'lucide-react';

const QUICK_TOPICS = [
  { label: 'Love', emoji: '❤️' },
  { label: 'Death', emoji: '💀' },
  { label: 'War', emoji: '⚔️' },
  { label: 'Women', emoji: '♀️' },
  { label: 'Afterlife', emoji: '✨' },
  { label: 'Money', emoji: '💰' },
  { label: 'Sin', emoji: '🔥' },
  { label: 'Forgiveness', emoji: '🕊️' },
];

const FEATURES = [
  {
    icon: BookOpen,
    title: 'Ask the Scriptures',
    description:
      'Ask any question and receive answers grounded exclusively in sacred scripture — with every claim cited.',
    href: '/query',
    color: 'text-indigo-600',
    bg: 'bg-indigo-50',
  },
  {
    icon: Scale,
    title: 'Compare Traditions',
    description:
      'See what Christianity, Islam, Hinduism, Buddhism, Judaism, and Sikhism each say about the same topic — side by side.',
    href: '/compare',
    color: 'text-violet-600',
    bg: 'bg-violet-50',
  },
  {
    icon: Swords,
    title: 'Scripture Debate',
    description:
      "Pose a question and watch each tradition's scriptures respond independently, revealing agreements and tensions.",
    href: '/debate',
    color: 'text-rose-600',
    bg: 'bg-rose-50',
  },
  {
    icon: Compass,
    title: 'Topic Explorer',
    description:
      'Browse curated topics across universal themes, ethics, society, and spirituality. Find connections you never expected.',
    href: '/explore',
    color: 'text-emerald-600',
    bg: 'bg-emerald-50',
  },
];

const TRADITIONS = [
  { name: 'Christianity', emoji: '✝️', text: 'KJV Bible', color: '#3B82F6' },
  { name: 'Islam', emoji: '☪️', text: 'Quran (Sahih Int.)', color: '#10B981' },
  { name: 'Hinduism', emoji: '🕉️', text: 'Bhagavad Gita', color: '#F59E0B' },
  { name: 'Buddhism', emoji: '☸️', text: 'Dhammapada', color: '#EAB308' },
  { name: 'Judaism', emoji: '✡️', text: 'Torah / Tanakh', color: '#8B5CF6' },
  { name: 'Sikhism', emoji: '🪯', text: 'Guru Granth Sahib', color: '#14B8A6' },
];

export default function HomePage() {
  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-b from-indigo-950 via-indigo-900 to-indigo-800 px-4 py-24 text-center text-white">
        {/* Decorative orbs */}
        <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-violet-600/20 blur-3xl" />
        <div className="pointer-events-none absolute -right-32 bottom-0 h-96 w-96 rounded-full bg-indigo-400/20 blur-3xl" />

        <div className="relative mx-auto max-w-4xl">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-sm backdrop-blur-sm">
            <Sparkles size={14} className="text-yellow-300" />
            AI-powered scripture exploration
          </div>

          <h1 className="mb-6 text-5xl font-extrabold leading-tight sm:text-6xl">
            What does every religion say
            <br />
            <span className="bg-gradient-to-r from-yellow-300 to-orange-300 bg-clip-text text-transparent">
              about any topic?
            </span>
          </h1>

          <p className="mx-auto mb-10 max-w-2xl text-lg text-indigo-200">
            CrossVerse uses AI retrieval to surface relevant scripture from six major
            traditions. Every answer is grounded in text — no opinion, no commentary,
            always cited.
          </p>

          {/* CTA buttons */}
          <div className="flex flex-wrap justify-center gap-4">
            <Link
              href="/query"
              className="flex items-center gap-2 rounded-xl bg-white px-6 py-3 font-semibold text-indigo-900 hover:bg-indigo-50 transition-colors shadow-lg"
            >
              Ask a Question <ArrowRight size={18} />
            </Link>
            <Link
              href="/compare"
              className="flex items-center gap-2 rounded-xl border border-white/30 bg-white/10 px-6 py-3 font-semibold text-white hover:bg-white/20 transition-colors backdrop-blur-sm"
            >
              Compare Traditions
            </Link>
          </div>
        </div>
      </section>

      {/* Quick Topics */}
      <section className="border-b border-gray-200 bg-white px-4 py-8 dark:border-gray-800 dark:bg-gray-900">
        <div className="mx-auto max-w-5xl">
          <p className="mb-4 text-center text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
            Explore by topic
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            {QUICK_TOPICS.map(({ label, emoji }) => (
              <Link
                key={label}
                href={`/compare?topic=${encodeURIComponent(label)}`}
                className="flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:border-indigo-300 hover:text-indigo-700 transition-colors shadow-sm dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:border-indigo-600 dark:hover:text-indigo-400"
              >
                <span>{emoji}</span> {label}
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="px-4 py-16">
        <div className="mx-auto max-w-6xl">
          <h2 className="mb-3 text-center text-3xl font-bold text-gray-900 dark:text-gray-100">
            Four ways to explore scripture
          </h2>
          <p className="mb-10 text-center text-gray-500 dark:text-gray-400">
            From quick answers to deep cross-tradition analysis
          </p>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map(({ icon: Icon, title, description, href, color, bg }) => (
              <Link
                key={href}
                href={href}
                className="group rounded-2xl border border-gray-200 bg-white p-6 shadow-sm hover:shadow-md transition-all hover:-translate-y-1 dark:border-gray-700 dark:bg-gray-900 dark:hover:shadow-none dark:hover:border-gray-600"
              >
                <div className={`mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl ${bg} ${color} dark:bg-opacity-20`}>
                  <Icon size={24} />
                </div>
                <h3 className="mb-2 font-bold text-gray-900 dark:text-gray-100">{title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed dark:text-gray-400">{description}</p>
                <div className={`mt-4 flex items-center gap-1 text-sm font-medium ${color} opacity-0 group-hover:opacity-100 transition-opacity`}>
                  Explore <ArrowRight size={14} />
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Traditions */}
      <section className="bg-gray-900 px-4 py-16 text-white">
        <div className="mx-auto max-w-5xl">
          <h2 className="mb-3 text-center text-3xl font-bold">Six Sacred Traditions</h2>
          <p className="mb-10 text-center text-gray-400">
            Authentic scripture, faithfully sourced and embedded for semantic search
          </p>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {TRADITIONS.map(({ name, emoji, text, color }) => (
              <div
                key={name}
                className="flex items-center gap-4 rounded-xl border border-white/10 bg-white/5 p-4"
              >
                <div
                  className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-2xl"
                  style={{ backgroundColor: `${color}22` }}
                >
                  {emoji}
                </div>
                <div>
                  <div className="font-bold text-white">{name}</div>
                  <div className="text-sm text-gray-400">{text}</div>
                </div>
                <div
                  className="ml-auto h-2 w-2 rounded-full"
                  style={{ backgroundColor: color }}
                />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="px-4 py-16">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="mb-3 text-3xl font-bold text-gray-900 dark:text-gray-100">How it works</h2>
          <p className="mb-10 text-gray-500 dark:text-gray-400">Grounded, transparent, and citation-first</p>
          <div className="grid gap-8 sm:grid-cols-3">
            {[
              { step: '1', title: 'You ask', desc: 'Type any theological, ethical, or philosophical question.' },
              { step: '2', title: 'We retrieve', desc: 'Semantic search finds the most relevant passages from across all traditions.' },
              { step: '3', title: 'AI synthesizes', desc: 'The answer is generated using ONLY the retrieved passages — always cited, never opinionated.' },
            ].map(({ step, title, desc }) => (
              <div key={step} className="flex flex-col items-center">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-indigo-600 text-lg font-extrabold text-white">
                  {step}
                </div>
                <h3 className="mb-1 font-bold text-gray-900 dark:text-gray-100">{title}</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer CTA */}
      <section className="border-t border-gray-200 bg-white px-4 py-12 text-center dark:border-gray-800 dark:bg-gray-900">
        <h2 className="mb-3 text-2xl font-bold text-gray-900 dark:text-gray-100">
          Ready to explore?
        </h2>
        <p className="mb-6 text-gray-500 dark:text-gray-400">Start with a question, a comparison, or a debate.</p>
        <Link
          href="/query"
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-8 py-3 font-semibold text-white hover:bg-indigo-700 transition-colors shadow-lg"
        >
          Get Started <ArrowRight size={18} />
        </Link>
      </section>
    </div>
  );
}
