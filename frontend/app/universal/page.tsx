'use client';

import { useState } from 'react';
import { Sparkles } from 'lucide-react';
import { findUniversalTruth } from '@/lib/api';
import type { UniversalResponse } from '@/lib/types';
import { RELIGION_COLORS, RELIGION_EMOJI, ALL_RELIGIONS } from '@/lib/types';
import VerseCard from '@/components/ui/VerseCard';

const QUICK_CONCEPTS = [
  'Love', 'Death', 'Suffering', 'Justice', 'Peace',
  'Forgiveness', 'Compassion', 'Gratitude', 'Truth', 'Humility',
];

export default function UniversalPage() {
  const [concept, setConcept] = useState('');
  const [result, setResult] = useState<UniversalResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visibleCards, setVisibleCards] = useState(0);

  async function search(query: string) {
    if (!query.trim()) return;
    setConcept(query);
    setLoading(true);
    setError(null);
    setResult(null);
    setVisibleCards(0);
    try {
      const data = await findUniversalTruth({ concept: query });
      setResult(data);
      // Stagger cards in
      let count = 0;
      const interval = setInterval(() => {
        count += 1;
        setVisibleCards(count);
        if (count >= 6) clearInterval(interval);
      }, 150);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    search(concept);
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Header */}
      <div className="bg-gradient-to-br from-indigo-950 via-indigo-900 to-violet-900 px-4 py-14 text-white">
        <div className="mx-auto max-w-3xl text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-sm backdrop-blur-sm">
            <Sparkles size={14} className="text-yellow-300" />
            117,000+ verses · 6 traditions
          </div>
          <h1 className="mb-3 text-4xl font-extrabold sm:text-5xl">Universal Truth</h1>
          <p className="text-indigo-200">
            What do all six traditions agree on? Enter any concept and find out.
          </p>
        </div>
      </div>

      <div className="mx-auto max-w-4xl px-4 py-8">
        {/* Search */}
        <form onSubmit={handleSubmit} className="mb-6">
          <div className="flex gap-3">
            <input
              type="text"
              value={concept}
              onChange={(e) => setConcept(e.target.value)}
              placeholder="Enter a concept (e.g. compassion, justice, suffering)…"
              className="flex-1 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm shadow-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-200 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100 dark:focus:border-indigo-500 dark:focus:ring-indigo-800"
            />
            <button
              type="submit"
              disabled={!concept.trim() || loading}
              className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              <Sparkles size={15} />
              Discover
            </button>
          </div>
        </form>

        {/* Quick pills */}
        <div className="mb-8 flex flex-wrap gap-2">
          {QUICK_CONCEPTS.map((c) => (
            <button
              key={c}
              onClick={() => search(c)}
              className="rounded-full border border-gray-200 bg-white px-4 py-1.5 text-sm font-medium text-gray-600 hover:border-indigo-300 hover:text-indigo-700 transition-colors dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:border-indigo-600 dark:hover:text-indigo-300"
            >
              {c}
            </button>
          ))}
        </div>

        {/* Loading */}
        {loading && (
          <div className="py-16 text-center">
            <p className="animate-pulse text-lg italic text-gray-500 dark:text-gray-400">
              Searching 117,000+ verses across 6 traditions…
            </p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
            {error}
          </div>
        )}

        {/* Result */}
        {result && !loading && (
          <div className="space-y-8">
            {/* Universal truth banner */}
            <div className="rounded-2xl bg-gradient-to-br from-indigo-950 via-indigo-900 to-violet-900 p-8 text-white shadow-xl">
              <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-indigo-300">
                The Universal Teaching:
              </p>
              <p className="text-2xl font-bold leading-snug sm:text-3xl">
                {result.universal_truth}
              </p>
            </div>

            {/* Tradition cards */}
            <div>
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                How each tradition expresses it
              </h2>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {ALL_RELIGIONS.map((religion, index) => {
                  const expr = result.tradition_expressions[religion];
                  if (!expr) return null;
                  const color = RELIGION_COLORS[religion];
                  const emoji = RELIGION_EMOJI[religion];
                  const isVisible = index < visibleCards;

                  return (
                    <div
                      key={religion}
                      className={`rounded-2xl border bg-white p-5 shadow-sm dark:bg-gray-900 ${
                        isVisible ? 'verse-card-visible' : 'verse-card-enter'
                      }`}
                      style={{ borderColor: `${color}66` }}
                    >
                      <div className="mb-3 flex items-center gap-2">
                        <span className="text-xl">{emoji}</span>
                        <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                          {religion}
                        </span>
                      </div>
                      <p className="mb-3 text-sm italic text-gray-600 leading-relaxed dark:text-gray-400 line-clamp-3">
                        &ldquo;{expr.verse_text}&rdquo;
                      </p>
                      <p
                        className="mb-2 text-xs font-medium"
                        style={{ color }}
                      >
                        {expr.reference}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {expr.reflection}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Sources */}
            {result.sources.length > 0 && (
              <details className="group">
                <summary className="cursor-pointer list-none">
                  <div className="flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                    <span className="group-open:hidden">▶</span>
                    <span className="hidden group-open:inline">▼</span>
                    {result.sources.length} source passages
                  </div>
                </summary>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  {result.sources.map((chunk, i) => (
                    <VerseCard key={chunk.id ?? i} chunk={chunk} index={i} compact />
                  ))}
                </div>
              </details>
            )}
          </div>
        )}

        {/* Empty state */}
        {!result && !loading && !error && (
          <div className="py-16 text-center text-gray-400 dark:text-gray-500">
            <Sparkles size={48} className="mx-auto mb-4 opacity-30" />
            <p className="text-lg">Enter a concept above to find the universal truth across all traditions</p>
          </div>
        )}
      </div>
    </div>
  );
}
