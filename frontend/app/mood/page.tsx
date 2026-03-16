'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { getMoodScripture } from '@/lib/api';
import type { MoodResponse, MoodType } from '@/lib/types';
import VerseCard from '@/components/ui/VerseCard';

const MOODS: { label: string; emoji: string; value: MoodType; color: string }[] = [
  { label: 'Grief', emoji: '🌧️', value: 'grief', color: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300' },
  { label: 'Joy', emoji: '☀️', value: 'joy', color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300' },
  { label: 'Anxiety', emoji: '🌊', value: 'anxiety', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' },
  { label: 'Fear', emoji: '😰', value: 'fear', color: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300' },
  { label: 'Hope', emoji: '🌿', value: 'hope', color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' },
  { label: 'Loneliness', emoji: '🕯️', value: 'loneliness', color: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' },
  { label: 'Anger', emoji: '🔥', value: 'anger', color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' },
  { label: 'Gratitude', emoji: '🙏', value: 'gratitude', color: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300' },
  { label: 'Confusion', emoji: '🌀', value: 'confusion', color: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300' },
  { label: 'Love', emoji: '❤️', value: 'love', color: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300' },
];

const MOOD_GRADIENT: Record<MoodType, string> = {
  grief: 'from-slate-700 to-slate-900',
  joy: 'from-amber-500 to-yellow-600',
  anxiety: 'from-blue-600 to-cyan-700',
  fear: 'from-purple-700 to-indigo-900',
  hope: 'from-emerald-600 to-teal-700',
  loneliness: 'from-orange-600 to-amber-800',
  anger: 'from-red-600 to-rose-800',
  gratitude: 'from-teal-600 to-emerald-700',
  confusion: 'from-indigo-600 to-violet-800',
  love: 'from-rose-500 to-pink-700',
};

const VALID_MOODS = new Set<MoodType>(MOODS.map((m) => m.value));

function isValidMood(s: string | null): s is MoodType {
  return s !== null && VALID_MOODS.has(s as MoodType);
}

function MoodContent() {
  const searchParams = useSearchParams();
  const paramMood = searchParams.get('mood');
  const [activeMood, setActiveMood] = useState<MoodType | null>(
    isValidMood(paramMood) ? paramMood : null
  );
  const [result, setResult] = useState<MoodResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function fetchMood(mood: MoodType) {
    setActiveMood(mood);
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await getMoodScripture({ mood });
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (activeMood) {
      fetchMood(activeMood);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const moodMeta = MOODS.find((m) => m.value === activeMood);
  const gradient = activeMood ? MOOD_GRADIENT[activeMood] : 'from-indigo-600 to-indigo-800';

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Header */}
      <div className={`bg-gradient-to-br ${gradient} px-4 py-12 text-white`}>
        <div className="mx-auto max-w-3xl text-center">
          <h1 className="mb-2 text-3xl font-extrabold sm:text-4xl">
            {moodMeta ? (
              <>
                <span className="mr-2">{moodMeta.emoji}</span>
                {moodMeta.label}
              </>
            ) : (
              'How are you feeling?'
            )}
          </h1>
          <p className="text-white/70">Scripture that meets you where you are</p>
        </div>
      </div>

      <div className="mx-auto max-w-4xl px-4 py-8">
        {/* Mood pills */}
        <div className="mb-8 flex flex-wrap justify-center gap-2">
          {MOODS.map(({ label, emoji, value, color }) => (
            <button
              key={value}
              onClick={() => fetchMood(value)}
              className={`flex items-center gap-1.5 rounded-full border px-4 py-2 text-sm font-medium transition-all ${
                activeMood === value
                  ? `${color} border-transparent ring-2 ring-offset-2 ring-indigo-400 dark:ring-offset-gray-950`
                  : 'border-gray-200 bg-white text-gray-700 hover:border-indigo-300 hover:text-indigo-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300'
              }`}
            >
              <span>{emoji}</span> {label}
            </button>
          ))}
        </div>

        {/* Loading */}
        {loading && activeMood && (
          <div className="py-16 text-center">
            <p className="animate-pulse text-lg italic text-gray-500 dark:text-gray-400">
              The scriptures speak to {activeMood}…
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
            {/* Wisdom message */}
            <div className={`rounded-2xl bg-gradient-to-br ${gradient} p-6 text-white shadow-lg`}>
              <p className="text-lg italic leading-relaxed">{result.message}</p>
            </div>

            {/* Verses */}
            <div>
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Passages from all traditions
              </h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {result.verses.map((chunk, i) => (
                  <VerseCard key={chunk.id ?? i} chunk={chunk} index={i} compact />
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Empty state */}
        {!activeMood && !loading && (
          <div className="py-16 text-center text-gray-400 dark:text-gray-500">
            <p className="text-lg">Select a mood above to receive wisdom from scripture</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function MoodPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-gray-50 dark:bg-gray-950" />}>
      <MoodContent />
    </Suspense>
  );
}
