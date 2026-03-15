'use client';

import { useEffect, useState } from 'react';
import { getDailyBriefing } from '@/lib/api';
import {
  type DailyResponse,
  type Religion,
  ALL_RELIGIONS,
  RELIGION_COLORS,
  RELIGION_EMOJI,
} from '@/lib/types';
import VerseCard from '@/components/ui/VerseCard';
import { Calendar, Loader2, RefreshCw } from 'lucide-react';

export default function DailyPage() {
  const [result, setResult] = useState<DailyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async (fresh = false) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDailyBriefing(fresh);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load daily briefing.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(false);
  }, []);

  const formatted = result
    ? new Date(result.date + 'T00:00:00').toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    : '';

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-full bg-amber-100 text-amber-600 dark:bg-amber-900/40 dark:text-amber-400">
          <Calendar size={24} />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Daily Scripture Briefing</h1>
        {result && (
          <p className="mt-2 text-gray-500 dark:text-gray-400">
            Today is <span className="font-semibold text-gray-700 dark:text-gray-300">{formatted}</span>
          </p>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-20 gap-4 text-gray-500 dark:text-gray-400">
          <Loader2 size={32} className="animate-spin" />
          <p>Gathering today&apos;s wisdom from all traditions…</p>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-900/20 dark:text-red-400">
          {error}
          <button
            onClick={load}
            className="ml-3 underline hover:no-underline"
          >
            Retry
          </button>
        </div>
      )}

      {/* Result */}
      {result && !loading && (
        <>
          {/* Theme banner */}
          <div className="mb-8 rounded-2xl bg-gradient-to-r from-indigo-900 to-violet-900 p-8 text-center text-white">
            <p className="mb-1 text-sm font-semibold uppercase tracking-widest text-indigo-300">
              Today&apos;s Theme
            </p>
            <h2 className="text-4xl font-extrabold capitalize">{result.theme}</h2>
          </div>

          {/* Refresh */}
          <div className="mb-6 flex justify-end">
            <button
              onClick={() => load(true)}
              className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors dark:border-gray-700 dark:text-gray-400 dark:hover:bg-gray-800"
            >
              <RefreshCw size={12} />
              New Theme
            </button>
          </div>

          {/* Religion cards grid */}
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {ALL_RELIGIONS.map((religion) => {
              const perspective = result.perspectives[religion as Religion];
              if (!perspective) return null;
              const color = RELIGION_COLORS[religion as Religion];
              return (
                <div
                  key={religion}
                  className="rounded-2xl border-2 bg-white p-5 shadow-sm dark:bg-gray-900"
                  style={{ borderColor: color }}
                >
                  <div className="mb-3 flex items-center gap-2">
                    <span className="text-2xl">{RELIGION_EMOJI[religion as Religion]}</span>
                    <h3 className="font-bold text-gray-900 dark:text-gray-100">{religion}</h3>
                  </div>

                  {/* Reflection */}
                  <p className="mb-4 text-sm leading-relaxed text-gray-700 italic dark:text-gray-300">
                    {perspective.reflection}
                  </p>

                  {/* Verses */}
                  {perspective.sources.length > 0 && (
                    <div className="space-y-2">
                      {perspective.sources.map((v) => (
                        <VerseCard key={v.id} chunk={v} compact />
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
