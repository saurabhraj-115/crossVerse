'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, RefreshCw, Sparkles } from 'lucide-react';
import { getDailyBriefing } from '@/lib/api';
import type { DailyResponse } from '@/lib/types';
import { RELIGION_COLORS, RELIGION_EMOJI, ALL_RELIGIONS } from '@/lib/types';

function SkeletonGrid() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="animate-pulse rounded-2xl border border-white/10 bg-white/5 p-5 h-40"
        />
      ))}
    </div>
  );
}

function CardGrid({
  daily,
  visibleCards,
}: {
  daily: DailyResponse;
  visibleCards: number;
}) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {ALL_RELIGIONS.map((religion, index) => {
        const perspective = daily.perspectives[religion];
        if (!perspective) return null;
        const color = RELIGION_COLORS[religion];
        const emoji = RELIGION_EMOJI[religion];
        const firstSource = perspective.sources[0];
        const isVisible = index < visibleCards;

        return (
          <Link
            key={religion}
            href="/daily"
            className={`block rounded-2xl border bg-white/5 p-5 hover:bg-white/10 transition-colors cursor-pointer ${
              isVisible ? 'verse-card-visible' : 'verse-card-enter'
            }`}
            style={{ borderColor: `${color}44` }}
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
  const [daily, setDaily] = useState<DailyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [visibleCards, setVisibleCards] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  async function fetchDaily(fresh = false) {
    if (fresh) setRefreshing(true);
    setLoading(true);
    setVisibleCards(0);
    try {
      const data = await getDailyBriefing(fresh);
      setDaily(data);
      // Stagger cards in after data lands
      let count = 0;
      const interval = setInterval(() => {
        count += 1;
        setVisibleCards(count);
        if (count >= 6) clearInterval(interval);
      }, 150);
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

  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-indigo-950 via-indigo-900 to-indigo-800 px-4 py-16 text-white">
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
                Today, all 6 traditions speak about:
              </p>
              <h1 className="text-4xl font-extrabold capitalize sm:text-5xl">
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

        {/* Cards */}
        <div className="mb-8">
          {loading ? (
            <SkeletonGrid />
          ) : daily ? (
            <CardGrid daily={daily} visibleCards={visibleCards} />
          ) : null}
        </div>

        {/* CTAs */}
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/query"
            className="flex items-center gap-2 rounded-xl bg-white px-5 py-2.5 text-sm font-semibold text-indigo-900 hover:bg-indigo-50 transition-colors shadow-lg"
          >
            Ask Your Own Question <ArrowRight size={16} />
          </Link>
          <Link
            href="/fingerprint"
            className="flex items-center gap-2 rounded-xl border border-white/30 bg-white/10 px-5 py-2.5 text-sm font-semibold text-white hover:bg-white/20 transition-colors backdrop-blur-sm"
          >
            Find Your Tradition
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
