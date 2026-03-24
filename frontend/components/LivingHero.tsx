'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowRight, RefreshCw, Sparkles, Send } from 'lucide-react';
import { getDailyBriefing } from '@/lib/api';
import type { DailyResponse } from '@/lib/types';
import { RELIGION_COLORS, RELIGION_EMOJI, ALL_RELIGIONS } from '@/lib/types';

const LOADING_QUOTES = [
  '"Be still and know." — Psalm 46:10',
  '"The quieter you become, the more you can hear." — Ram Dass',
  '"Peace comes from within." — Dhammapada',
  '"In remembrance of God do hearts find rest." — Quran 13:28',
  '"Silence is the language of God." — Rumi',
  '"The Tao that can be told is not the eternal Tao." — Tao Te Ching',
  '"Where there is love, there is life." — Gandhi',
  '"Let your soul stand cool and composed." — Walt Whitman',
];

function SkeletonGrid() {
  const [quoteIdx, setQuoteIdx] = useState(() => Math.floor(Math.random() * LOADING_QUOTES.length));

  useEffect(() => {
    const t = setInterval(() => setQuoteIdx((i) => (i + 1) % LOADING_QUOTES.length), 2500);
    return () => clearInterval(t);
  }, []);

  return (
    <div>
      <p className="mb-5 text-center text-sm italic text-indigo-300 animate-pulse transition-all">
        {LOADING_QUOTES[quoteIdx]}
      </p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 12 }).map((_, i) => (
          <div
            key={i}
            className="animate-pulse rounded-2xl border border-white/10 bg-white/5 p-5 h-40"
          />
        ))}
      </div>
    </div>
  );
}

function CardGrid({ daily }: { daily: DailyResponse }) {
  // Only render traditions that have perspectives, preserving canonical order
  const entries = ALL_RELIGIONS.filter((r) => daily.perspectives[r] != null);

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {entries.map((religion, index) => {
        const perspective = daily.perspectives[religion]!;
        const color = RELIGION_COLORS[religion];
        const emoji = RELIGION_EMOJI[religion];
        const firstSource = perspective.sources[0];

        return (
          <Link
            key={religion}
            href="/daily"
            className="block rounded-2xl border bg-white/5 p-5 hover:bg-white/10 transition-colors cursor-pointer card-animate-in"
            style={{
              borderColor: `${color}44`,
              animationDelay: `${index * 120}ms`,
            }}
          >
            <div className="mb-3 flex items-center gap-2">
              <span className="text-xl">{emoji}</span>
              <span className="text-sm font-semibold text-white/90">{religion}</span>
            </div>
            <p className="text-sm text-white/70 leading-relaxed line-clamp-3">
              {perspective.reflection}
            </p>
            {firstSource && (
              <p className="mt-3 text-xs font-medium" style={{ color: `${color}cc` }}>
                {firstSource.reference}
              </p>
            )}
          </Link>
        );
      })}
    </div>
  );
}

export default function LivingHero() {
  const router = useRouter();
  const [daily, setDaily] = useState<DailyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [question, setQuestion] = useState('');

  const handleAsk = (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    router.push(`/query?q=${encodeURIComponent(question.trim())}`);
  };

  async function fetchDaily(fresh = false) {
    if (fresh) {
      setRefreshing(true);
      setDaily(null); // immediately clear so title resets while loading
    }
    setLoading(true);
    try {
      const data = await getDailyBriefing(fresh);
      setDaily(data);
    } catch {
      // silently fail — hero degrades gracefully
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    fetchDaily(false);
  }, []);

  const formattedDate = daily?.date
    ? new Date(daily.date + 'T00:00:00').toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
      })
    : null;

  const traditionCount = daily ? Object.keys(daily.perspectives).length : null;

  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-indigo-950 via-indigo-900 to-indigo-800 px-4 py-10 text-white">
      <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-violet-600/20 blur-3xl" />
      <div className="pointer-events-none absolute -right-32 bottom-0 h-96 w-96 rounded-full bg-indigo-400/20 blur-3xl" />

      <div className="relative mx-auto max-w-5xl">
        {/* Badge */}
        <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-sm backdrop-blur-sm">
          <Sparkles size={14} className="text-yellow-300" />
          AI-powered scripture exploration
        </div>

        {/* Header */}
        <div className="mb-8">
          {daily ? (
            <>
              <p className="mb-1 text-sm font-medium uppercase tracking-wider text-indigo-300">
                Today, all {traditionCount} traditions speak about:
              </p>
              <h1 className="text-3xl font-extrabold capitalize sm:text-4xl md:text-5xl">
                <span className="bg-gradient-to-r from-yellow-300 to-orange-300 bg-clip-text text-transparent">
                  {daily.theme}
                </span>
              </h1>
              {formattedDate && (
                <p className="mt-2 text-sm text-indigo-300">{formattedDate}</p>
              )}
            </>
          ) : (
            <div className="space-y-3">
              <div className="h-4 w-48 animate-pulse rounded bg-white/20" />
              <div className="h-10 w-80 animate-pulse rounded bg-white/20" />
            </div>
          )}
        </div>

        {/* Ask box — primary CTA */}
        <form onSubmit={handleAsk} className="mb-10">
          <div className="flex items-center gap-2 rounded-2xl border border-white/20 bg-white/10 p-2 backdrop-blur-sm focus-within:border-white/40 focus-within:bg-white/15 transition-all shadow-lg">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask anything — grief, purpose, forgiveness, what happens after death…"
              className="flex-1 bg-transparent px-3 py-2 text-sm text-white placeholder-white/50 outline-none sm:text-base"
            />
            <button
              type="submit"
              disabled={!question.trim()}
              className="flex shrink-0 items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-indigo-900 hover:bg-indigo-50 disabled:opacity-40 transition-colors shadow"
            >
              <Send size={15} />
              <span className="hidden sm:inline">Ask Scripture</span>
            </button>
          </div>
          <p className="mt-2 px-1 text-xs text-indigo-300/80">
            Answers from 12 traditions · always cited · never opinionated
          </p>
        </form>

        {/* Cards */}
        <div className="mb-8">
          {loading ? (
            <SkeletonGrid />
          ) : daily ? (
            <CardGrid daily={daily} />
          ) : null}
        </div>

        {/* Secondary CTAs */}
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/fingerprint"
            className="flex items-center gap-2 rounded-xl border border-white/30 bg-white/10 px-5 py-2.5 text-sm font-semibold text-white hover:bg-white/20 transition-colors backdrop-blur-sm"
          >
            Find Your Tradition <ArrowRight size={15} />
          </Link>
          <button
            onClick={() => fetchDaily(true)}
            disabled={refreshing}
            className="flex items-center gap-2 rounded-xl border border-white/20 bg-white/5 px-5 py-2.5 text-sm font-semibold text-white/80 hover:bg-white/10 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
            Different Theme
          </button>
        </div>
      </div>
    </section>
  );
}
