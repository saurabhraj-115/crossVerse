'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight, BookOpen, Download, RefreshCw, Send, Share2, Sparkles, X } from 'lucide-react';
import Link from 'next/link';
import type { DailyResponse, DailyPerspective, Religion } from '@/lib/types';
import { RELIGION_COLORS, RELIGION_EMOJI, ALL_RELIGIONS } from '@/lib/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ---------------------------------------------------------------------------
// Share card canvas generator
// ---------------------------------------------------------------------------
function wrapCanvasText(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  lineHeight: number,
): number {
  const words = text.split(' ');
  let line = '';
  let curY = y;
  for (const word of words) {
    const test = line + word + ' ';
    if (ctx.measureText(test).width > maxWidth && line) {
      ctx.fillText(line.trim(), x, curY);
      line = word + ' ';
      curY += lineHeight;
    } else {
      line = test;
    }
  }
  if (line.trim()) ctx.fillText(line.trim(), x, curY);
  return curY;
}

async function generateShareCard(
  religion: string,
  color: string,
  emoji: string,
  theme: string,
  reflection: string,
  reference: string,
): Promise<Blob> {
  return new Promise((resolve) => {
    const W = 1080, H = 1350;
    const canvas = document.createElement('canvas');
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext('2d')!;

    // Background
    const bg = ctx.createLinearGradient(0, 0, 0, H);
    bg.addColorStop(0, '#06071a');
    bg.addColorStop(1, '#0e0f2e');
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, W, H);

    // Colored glow blob top-right
    const glow = ctx.createRadialGradient(W * 0.8, H * 0.1, 0, W * 0.8, H * 0.1, 400);
    glow.addColorStop(0, `${color}30`);
    glow.addColorStop(1, 'transparent');
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, W, H);

    // Top color bar
    ctx.fillStyle = color;
    ctx.fillRect(0, 0, W, 10);

    // "LIVE TODAY" badge
    ctx.fillStyle = `${color}22`;
    const badgeW = 200, badgeH = 44, badgeX = W / 2 - badgeW / 2, badgeY = 60;
    ctx.beginPath();
    ctx.roundRect(badgeX, badgeY, badgeW, badgeH, 22);
    ctx.fill();
    ctx.font = 'bold 18px system-ui, sans-serif';
    ctx.fillStyle = color;
    ctx.textAlign = 'center';
    ctx.fillText('LIVE TODAY · CROSSVERSE', W / 2, badgeY + 28);

    // Emoji
    ctx.font = '140px serif';
    ctx.textAlign = 'center';
    ctx.fillText(emoji, W / 2, 290);

    // Religion name
    ctx.font = 'bold 72px system-ui, sans-serif';
    ctx.fillStyle = '#ffffff';
    ctx.fillText(religion, W / 2, 390);

    // "on <theme>" pill
    const themeText = `on: ${theme}`;
    ctx.font = '32px system-ui, sans-serif';
    ctx.fillStyle = `${color}cc`;
    ctx.fillText(themeText, W / 2, 450);

    // Divider
    ctx.strokeStyle = `${color}44`;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(140, 490);
    ctx.lineTo(W - 140, 490);
    ctx.stroke();

    // Reflection text
    const truncated = reflection.length > 320
      ? reflection.slice(0, 320).trimEnd() + '…'
      : reflection;
    ctx.font = 'italic 34px Georgia, serif';
    ctx.fillStyle = 'rgba(255,255,255,0.88)';
    ctx.textAlign = 'center';
    const lastY = wrapCanvasText(ctx, `"${truncated}"`, W / 2, 560, 800, 52);

    // Reference
    ctx.font = 'bold 28px system-ui, sans-serif';
    ctx.fillStyle = `${color}cc`;
    ctx.textAlign = 'center';
    const refY = Math.max(lastY + 70, 980);
    ctx.fillText(reference, W / 2, Math.min(refY, 1040));

    // Bottom branding bar
    ctx.fillStyle = `${color}18`;
    ctx.fillRect(0, H - 110, W, 110);
    ctx.font = 'bold 26px system-ui, sans-serif';
    ctx.fillStyle = 'rgba(255,255,255,0.5)';
    ctx.textAlign = 'center';
    ctx.fillText('crossverse-frontend.fly.dev', W / 2, H - 68);
    ctx.font = '22px system-ui, sans-serif';
    ctx.fillStyle = 'rgba(255,255,255,0.3)';
    ctx.fillText('AI-powered scripture exploration across 12 traditions', W / 2, H - 36);

    canvas.toBlob((blob) => resolve(blob!), 'image/png');
  });
}

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
      <p className="mb-5 text-center text-sm italic text-indigo-500 dark:text-indigo-300 animate-pulse transition-all">
        {LOADING_QUOTES[quoteIdx]}
      </p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 12 }).map((_, i) => (
          <div key={i} className="animate-pulse rounded-2xl border border-indigo-100 bg-indigo-50 dark:border-white/10 dark:bg-white/5 p-5 h-40" />
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
  const [sharing, setSharing] = useState(false);
  const backdropRef = useRef<HTMLDivElement>(null);

  const firstRef = perspective.sources[0]?.reference ?? '';

  const handleDownload = async () => {
    setSharing(true);
    try {
      const blob = await generateShareCard(religion, color, emoji, theme, perspective.reflection, firstRef);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `crossverse-${religion.toLowerCase()}-${theme.replace(/\s+/g, '-')}.png`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setSharing(false);
    }
  };

  const handleWhatsApp = async () => {
    setSharing(true);
    try {
      const blob = await generateShareCard(religion, color, emoji, theme, perspective.reflection, firstRef);
      const file = new File([blob], `crossverse-${religion.toLowerCase()}.png`, { type: 'image/png' });
      const shareText = `${emoji} ${religion} on "${theme}"\n\n"${perspective.reflection.slice(0, 200)}${perspective.reflection.length > 200 ? '…' : ''}"\n\n— ${firstRef}\n\nExplore all 12 traditions: https://crossverse-frontend.fly.dev`;

      if (typeof navigator !== 'undefined' && navigator.share && (navigator as any).canShare?.({ files: [file] })) {
        await navigator.share({
          title: `${religion} on ${theme} — CrossVerse`,
          text: shareText,
          files: [file],
        });
      } else {
        window.open(`https://wa.me/?text=${encodeURIComponent(shareText)}`, '_blank');
      }
    } finally {
      setSharing(false);
    }
  };

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
        className="relative flex w-full max-w-lg flex-col rounded-t-3xl sm:rounded-2xl bg-white dark:bg-gray-950 shadow-2xl max-h-[90vh] overflow-hidden"
        style={{ borderTop: `3px solid ${color}` }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4" style={{ backgroundColor: `${color}18` }}>
          <div className="flex items-center gap-3">
            <span className="text-2xl">{emoji}</span>
            <div>
              <p className="font-bold text-gray-900 dark:text-white">{religion}</p>
              <p className="text-xs capitalize" style={{ color: `${color}cc` }}>on {theme}</p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={handleDownload}
              disabled={sharing}
              title="Download as image"
              className="flex h-8 w-8 items-center justify-center rounded-full text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-white/50 dark:hover:bg-white/10 dark:hover:text-white transition-colors disabled:opacity-40"
            >
              <Download size={15} />
            </button>
            <button
              onClick={handleWhatsApp}
              disabled={sharing}
              title="Share on WhatsApp"
              className="flex h-8 w-8 items-center justify-center rounded-full text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-white/50 dark:hover:bg-white/10 dark:hover:text-white transition-colors disabled:opacity-40"
            >
              <Share2 size={15} />
            </button>
            <button
              onClick={onClose}
              className="flex h-8 w-8 items-center justify-center rounded-full text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-white/50 dark:hover:bg-white/10 dark:hover:text-white transition-colors"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
          <p className="text-sm leading-relaxed text-gray-700 dark:text-white/85 italic">
            &ldquo;{perspective.reflection}&rdquo;
          </p>

          {perspective.sources.length > 0 && (
            <div>
              <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest" style={{ color: `${color}99` }}>
                Scripture sources
              </p>
              <div className="space-y-3">
                {perspective.sources.map((v) => (
                  <div
                    key={v.id}
                    className="rounded-xl border-l-2 bg-gray-50 dark:bg-white/5 px-4 py-3"
                    style={{ borderLeftColor: color }}
                  >
                    <div className="mb-1.5 flex items-center gap-1.5">
                      <BookOpen size={11} className="shrink-0 text-gray-400 dark:text-white/40" />
                      <span className="text-xs font-semibold text-gray-700 dark:text-white/70">{v.reference}</span>
                      {v.translation && (
                        <span className="ml-auto text-[10px] text-gray-400 dark:text-white/30">{v.translation}</span>
                      )}
                    </div>
                    <p className="text-sm leading-relaxed text-gray-700 dark:text-white/80 italic">
                      &ldquo;{v.text}&rdquo;
                    </p>
                    {v.book && (
                      <p className="mt-1.5 text-[10px] text-gray-400 dark:text-white/30">
                        {v.book}{v.chapter ? `, Ch. ${v.chapter}` : ''}{v.verse ? ` v. ${v.verse}` : ''}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <button
            onClick={handleThemeAsk}
            className="flex w-full items-center justify-between rounded-xl border border-gray-200 bg-gray-50 dark:border-white/10 dark:bg-white/5 px-4 py-3 text-left text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-white/70 dark:hover:bg-white/10 dark:hover:text-white transition-colors"
          >
            <span>What does {religion} say about <span className="font-semibold capitalize">{theme}</span>?</span>
            <ArrowRight size={14} className="shrink-0" />
          </button>
        </div>

        {/* Follow-up input */}
        <div className="border-t border-gray-100 dark:border-white/10 px-4 py-4">
          <form onSubmit={handleAsk} className="flex items-center gap-2 rounded-xl border border-gray-200 bg-gray-50 dark:border-white/20 dark:bg-white/5 px-3 py-2 focus-within:border-indigo-300 dark:focus-within:border-white/30 transition-colors">
            <input
              type="text"
              value={followUp}
              onChange={(e) => setFollowUp(e.target.value)}
              placeholder={`Ask ${religion} scripture anything…`}
              className="flex-1 bg-transparent text-sm text-gray-900 placeholder-gray-400 dark:text-white dark:placeholder-white/30 outline-none"
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
            className="block w-full rounded-2xl border bg-white/80 dark:bg-white/5 p-5 text-left hover:bg-white dark:hover:bg-white/10 transition-colors cursor-pointer card-animate-in shadow-sm dark:shadow-none"
            style={{
              borderColor: `${color}44`,
              animationDelay: `${index * 120}ms`,
            }}
          >
            <div className="mb-3 flex items-center gap-2">
              <span className="text-xl">{emoji}</span>
              <span className="text-sm font-semibold text-gray-900 dark:text-white/90">{religion}</span>
            </div>
            <p className="text-sm text-gray-600 dark:text-white/70 leading-relaxed line-clamp-3">
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

interface StreamTheme {
  theme: string;
  date: string;
  headline?: string | null;
}

export default function LivingHero() {
  const router = useRouter();
  const [streamTheme, setStreamTheme] = useState<StreamTheme | null>(null);
  const [perspectives, setPerspectives] = useState<Record<string, DailyPerspective>>({});
  const [loading, setLoading] = useState(true);  // true = skeleton showing
  const [done, setDone] = useState(false);        // true = all 12 streamed in
  const [refreshing, setRefreshing] = useState(false);
  const [question, setQuestion] = useState('');
  const [activeCard, setActiveCard] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  const handleAsk = (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    router.push(`/query?q=${encodeURIComponent(question.trim())}`);
  };

  function fetchDaily(fresh = false) {
    // Close any existing stream
    esRef.current?.close();

    if (fresh) {
      setRefreshing(true);
      setStreamTheme(null);
      setPerspectives({});
      setDone(false);
    }
    setLoading(true);

    const es = new EventSource(`${API_BASE}/daily/stream${fresh ? '?fresh=true' : ''}`);
    esRef.current = es;

    es.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === 'theme') {
          setStreamTheme({ theme: msg.theme, date: msg.date, headline: msg.headline });
          setLoading(false); // header is ready — drop the skeleton bars
        } else if (msg.type === 'card') {
          setPerspectives((prev) => ({ ...prev, [msg.religion]: msg.perspective }));
        } else if (msg.type === 'done') {
          setDone(true);
          setRefreshing(false);
          es.close();
        } else if (msg.type === 'error') {
          setLoading(false);
          setRefreshing(false);
          es.close();
        }
      } catch {
        // malformed event — ignore
      }
    };

    es.onerror = () => {
      setLoading(false);
      setRefreshing(false);
      es.close();
    };
  }

  useEffect(() => {
    fetchDaily(false);
    return () => esRef.current?.close();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);


  const formattedDate = streamTheme?.date
    ? new Date(streamTheme.date + 'T00:00:00').toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
      })
    : null;

  const traditionCount = Object.keys(perspectives).length || null;
  const activePerspective = activeCard ? perspectives[activeCard] : null;

  // Build a DailyResponse-shaped object for CardGrid / CardModal
  const dailyForCards = streamTheme
    ? { theme: streamTheme.theme, date: streamTheme.date, perspectives: perspectives as any, headline: streamTheme.headline }
    : null;

  return (
    <>
      <section className="relative overflow-hidden bg-gradient-to-b from-indigo-50 via-white to-indigo-50 dark:from-indigo-950 dark:via-indigo-900 dark:to-indigo-800 px-4 py-10">
        <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-indigo-200/40 dark:bg-violet-600/20 blur-3xl" />
        <div className="pointer-events-none absolute -right-32 bottom-0 h-96 w-96 rounded-full bg-indigo-100/60 dark:bg-indigo-400/20 blur-3xl" />

        <div className="relative mx-auto max-w-5xl">
          {/* Badge */}
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-100/80 text-indigo-700 dark:border-white/20 dark:bg-white/10 dark:text-white px-4 py-1.5 text-sm backdrop-blur-sm">
            <Sparkles size={14} className="text-yellow-500 dark:text-yellow-300" />
            AI-powered scripture exploration
          </div>

          {/* Header */}
          <div className="mb-8">
            {streamTheme ? (
              <>
                <p className="mb-1 text-sm font-medium uppercase tracking-wider text-indigo-600 dark:text-indigo-300">
                  Today, all {traditionCount ?? '…'} traditions speak about:
                </p>
                <h1 className="text-3xl font-extrabold capitalize sm:text-4xl md:text-5xl">
                  <span className="bg-gradient-to-r from-yellow-500 to-orange-500 dark:from-yellow-300 dark:to-orange-300 bg-clip-text text-transparent">
                    {streamTheme.theme}
                  </span>
                </h1>
                {streamTheme.headline && (() => {
                  const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(streamTheme.headline!)}&tbm=nws`;
                  return (
                    <a
                      href={searchUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-3 inline-flex max-w-full items-center gap-2 rounded-full border border-red-200 bg-red-50 hover:bg-red-100 dark:border-white/15 dark:bg-white/10 dark:hover:bg-white/15 px-3 py-1.5 backdrop-blur-sm transition-colors cursor-pointer"
                    >
                      <span className="flex h-2 w-2 shrink-0 rounded-full bg-red-500 animate-pulse" />
                      <span className="text-xs text-red-600 dark:text-white/60 font-medium uppercase tracking-wider shrink-0">Inspired by</span>
                      <span className="text-xs text-gray-800 dark:text-white/90 font-medium leading-snug truncate">"{streamTheme.headline}"</span>
                    </a>
                  );
                })()}
                {formattedDate && (
                  <p className="mt-2 text-sm text-indigo-500 dark:text-indigo-300">{formattedDate}</p>
                )}
              </>
            ) : (
              <div className="space-y-3">
                <div className="h-4 w-48 animate-pulse rounded bg-indigo-200 dark:bg-white/20" />
                <div className="h-10 w-80 animate-pulse rounded bg-indigo-200 dark:bg-white/20" />
              </div>
            )}
          </div>

          {/* Ask box — primary CTA */}
          <form onSubmit={handleAsk} className="mb-10">
            <div className="flex items-center gap-2 rounded-2xl border border-indigo-200 bg-white dark:border-white/20 dark:bg-white/10 p-2 backdrop-blur-sm focus-within:border-indigo-400 dark:focus-within:border-white/40 transition-all shadow-lg">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask anything — grief, purpose, forgiveness, what happens after death…"
                className="flex-1 bg-transparent px-3 py-2 text-sm text-gray-900 placeholder-gray-400 dark:text-white dark:placeholder-white/50 outline-none sm:text-base"
              />
              <button
                type="submit"
                disabled={!question.trim()}
                className="flex shrink-0 items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 dark:bg-white dark:text-indigo-900 dark:hover:bg-indigo-50 disabled:opacity-40 transition-colors shadow"
              >
                <Send size={15} />
                <span className="hidden sm:inline">Ask Scripture</span>
              </button>
            </div>
            <p className="mt-2 px-1 text-xs text-indigo-500 dark:text-indigo-300/80">
              Answers from 12 traditions · always cited · never opinionated
            </p>
          </form>

          {/* Cards */}
          <div className="mb-8">
            {loading ? (
              <SkeletonGrid />
            ) : (
              <>
                {dailyForCards && Object.keys(perspectives).length > 0 && (
                  <CardGrid daily={dailyForCards} onCardClick={setActiveCard} />
                )}
                {!done && streamTheme && (
                  <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {Array.from({ length: Math.max(0, 12 - Object.keys(perspectives).length) }).map((_, i) => (
                      <div key={i} className="animate-pulse rounded-2xl border border-indigo-100 bg-indigo-50 dark:border-white/10 dark:bg-white/5 p-5 h-40" />
                    ))}
                  </div>
                )}
              </>
            )}
          </div>

          {/* Secondary CTAs */}
          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/fingerprint"
              className="flex items-center gap-2 rounded-xl border border-indigo-300 bg-indigo-600 text-white hover:bg-indigo-700 dark:border-white/30 dark:bg-white/10 dark:text-white dark:hover:bg-white/20 px-5 py-2.5 text-sm font-semibold transition-colors backdrop-blur-sm"
            >
              Find Your Tradition <ArrowRight size={15} />
            </Link>
            <button
              onClick={() => fetchDaily(true)}
              disabled={refreshing}
              className="flex items-center gap-2 rounded-xl border border-indigo-200 bg-white text-indigo-700 hover:bg-indigo-50 dark:border-white/20 dark:bg-white/5 dark:text-white/80 dark:hover:bg-white/10 px-5 py-2.5 text-sm font-semibold transition-colors disabled:opacity-50"
            >
              <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
              Different Theme
            </button>
          </div>
        </div>
      </section>

      {/* Per-card modal */}
      {activeCard && activePerspective && streamTheme && (
        <CardModal
          religion={activeCard}
          perspective={activePerspective}
          theme={streamTheme.theme}
          onClose={() => setActiveCard(null)}
        />
      )}
    </>
  );
}
