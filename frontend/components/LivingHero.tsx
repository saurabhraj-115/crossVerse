'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight, BookOpen, RefreshCw, Send, Sparkles, X } from 'lucide-react';
import Link from 'next/link';
import { getDailyBriefing } from '@/lib/api';
import type { DailyResponse, DailyPerspective, Religion } from '@/lib/types';
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
          <div key={i} className="animate-pulse rounded-2xl border border-white/10 bg-white/5 p-5 h-40" />
        ))}
      </div>
    </div>
  );
}

interface CardModalProps {
  religion: string;
  perspective: DailyPerspective;
  theme: string;
  onClose: () => void;
}

function CardModal({ religion, perspective, theme, onClose }: CardModalProps) {
  const router = useRouter();
  const color = RELIGION_COLORS[religion as Religion];
  const emoji = RELIGION_EMOJI[religion as Religion];
  const [followUp, setFollowUp] = useState('');
  const backdropRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', h);
    // Prevent body scroll
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', h);
      document.body.style.overflow = '';
    };
  }, [onClose]);

  const handleAsk = (e: React.FormEvent) => {
    e.preventDefault();
    if (!followUp.trim()) return;
    router.push(`/query?q=${encodeURIComponent(followUp.trim())}&religions=${encodeURIComponent(religion)}`);
  };

  const handleThemeAsk = () => {
    router.push(`/query?q=${encodeURIComponent(`What does ${religion} say about ${theme}?`)}&religions=${encodeURIComponent(religion)}`);
  };

  return (
    <div
      ref={backdropRef}
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm p-0 sm:p-4"
      onMouseDown={(e) => { if (e.target === backdropRef.current) onClose(); }}
    >
      <div
        className="relative flex w-full max-w-lg flex-col rounded-t-3xl sm:rounded-2xl bg-gray-950 shadow-2xl max-h-[90vh] overflow-hidden"
        style={{ borderTop: `3px solid ${color}` }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4" style={{ backgroundColor: `${color}18` }}>
          <div className="flex items-center gap-3">
            <span className="text-2xl">{emoji}</span>
            <div>
              <p className="font-bold text-white">{religion}</p>
              <p className="text-xs capitalize" style={{ color: `${color}cc` }}>on {theme}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-full text-white/50 hover:bg-white/10 hover:text-white transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
          {/* Reflection */}
          <p className="text-sm leading-relaxed text-white/85 italic">
            &ldquo;{perspective.reflection}&rdquo;
          </p>

          {/* Source verses */}
          {perspective.sources.length > 0 && (
            <div>
              <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest" style={{ color: `${color}99` }}>
                Scripture sources
              </p>
              <div className="space-y-3">
                {perspective.sources.map((v) => (
                  <div
                    key={v.id}
                    className="rounded-xl border-l-2 bg-white/5 px-4 py-3"
                    style={{ borderLeftColor: color }}
                  >
                    <div className="mb-1.5 flex items-center gap-1.5">
                      <BookOpen size={11} className="shrink-0 text-white/40" />
                      <span className="text-xs font-semibold text-white/70">{v.reference}</span>
                      {v.translation && (
                        <span className="ml-auto text-[10px] text-white/30">{v.translation}</span>
                      )}
                    </div>
                    <p className="text-sm leading-relaxed text-white/80 italic">
                      &ldquo;{v.text}&rdquo;
                    </p>
                    {v.book && (
                      <p className="mt-1.5 text-[10px] text-white/30">
                        {v.book}{v.chapter ? `, Ch. ${v.chapter}` : ''}{v.verse ? ` v. ${v.verse}` : ''}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Quick action */}
          <button
            onClick={handleThemeAsk}
            className="flex w-full items-center justify-between rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-left text-sm text-white/70 hover:bg-white/10 hover:text-white transition-colors"
          >
            <span>What does {religion} say about <span className="font-semibold capitalize">{theme}</span>?</span>
            <ArrowRight size={14} className="shrink-0" />
          </button>
        </div>

        {/* Follow-up input */}
        <div className="border-t border-white/10 px-4 py-4">
          <form onSubmit={handleAsk} className="flex items-center gap-2 rounded-xl border border-white/20 bg-white/5 px-3 py-2 focus-within:border-white/30 transition-colors">
            <input
              type="text"
              value={followUp}
              onChange={(e) => setFollowUp(e.target.value)}
              placeholder={`Ask ${religion} scripture anything…`}
              className="flex-1 bg-transparent text-sm text-white placeholder-white/30 outline-none"
              autoFocus
            />
            <button
              type="submit"
              disabled={!followUp.trim()}
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg disabled:opacity-30 transition-colors"
              style={{ backgroundColor: color }}
            >
              <Send size={13} className="text-white" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

function CardGrid({
  daily,
  onCardClick,
}: {
  daily: DailyResponse;
  onCardClick: (religion: string) => void;
}) {
  const entries = ALL_RELIGIONS.filter((r) => daily.perspectives[r] != null);

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {entries.map((religion, index) => {
        const perspective = daily.perspectives[religion]!;
        const color = RELIGION_COLORS[religion];
        const emoji = RELIGION_EMOJI[religion];
        const firstSource = perspective.sources[0];

        return (
          <button
            key={religion}
            onClick={() => onCardClick(religion)}
            className="block w-full rounded-2xl border bg-white/5 p-5 text-left hover:bg-white/10 transition-colors cursor-pointer card-animate-in"
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
          </button>
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
  const [activeCard, setActiveCard] = useState<string | null>(null);

  const handleAsk = (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    router.push(`/query?q=${encodeURIComponent(question.trim())}`);
  };

  async function fetchDaily(fresh = false) {
    if (fresh) {
      setRefreshing(true);
      setDaily(null);
    }
    setLoading(true);
    try {
      const data = await getDailyBriefing(fresh);
      setDaily(data);
    } catch {
      // silently fail
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
  const activePerspective = activeCard && daily ? daily.perspectives[activeCard as Religion] : null;

  return (
    <>
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
              <CardGrid daily={daily} onCardClick={setActiveCard} />
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

      {/* Per-card modal */}
      {activeCard && activePerspective && daily && (
        <CardModal
          religion={activeCard}
          perspective={activePerspective}
          theme={daily.theme}
          onClose={() => setActiveCard(null)}
        />
      )}
    </>
  );
}
