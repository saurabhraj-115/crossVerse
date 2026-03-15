'use client';

import { useState } from 'react';
import { compareReligions } from '@/lib/api';
import {
  type CompareResponse,
  type Religion,
  ALL_RELIGIONS,
  RELIGION_COLORS,
  RELIGION_EMOJI,
} from '@/lib/types';
import VerseCard from '@/components/ui/VerseCard';
import { Scale, Loader2, Search } from 'lucide-react';
import clsx from 'clsx';

const QUICK_TOPICS = [
  'Love', 'Forgiveness', 'Prayer', 'Afterlife', 'Death',
  'War', 'Women', 'Charity', 'Sin', 'Soul',
];

export default function CompareView() {
  const [topic, setTopic] = useState('');
  const [selectedReligions, setSelectedReligions] = useState<Religion[]>([
    'Christianity', 'Islam', 'Hinduism',
  ]);
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleReligion = (religion: Religion) => {
    setSelectedReligions((prev) =>
      prev.includes(religion)
        ? prev.filter((r) => r !== religion)
        : [...prev, religion]
    );
  };

  const handleCompare = async (topicText: string = topic) => {
    if (!topicText.trim() || selectedReligions.length < 2) return;
    setLoading(true);
    setError(null);
    try {
      const data = await compareReligions({
        topic: topicText.trim(),
        religions: selectedReligions,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Comparison failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100 text-indigo-600 dark:bg-indigo-900/40 dark:text-indigo-400">
          <Scale size={24} />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Scripture Comparison</h1>
        <p className="mt-2 text-gray-500 dark:text-gray-400">
          See what multiple traditions say about the same topic, side by side.
        </p>
      </div>

      {/* Controls */}
      <div className="mb-8 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900">
        {/* Topic input */}
        <div className="mb-5">
          <label className="mb-1.5 block text-sm font-semibold text-gray-700 dark:text-gray-300">Topic</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCompare()}
              placeholder="e.g., forgiveness, afterlife, prayer…"
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500 dark:focus:border-indigo-500"
            />
            <button
              onClick={() => handleCompare()}
              disabled={!topic.trim() || selectedReligions.length < 2 || loading}
              className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40 transition-colors"
            >
              {loading ? <Loader2 size={15} className="animate-spin" /> : <Search size={15} />}
              Compare
            </button>
          </div>

          {/* Quick topics */}
          <div className="mt-3 flex flex-wrap gap-1.5">
            {QUICK_TOPICS.map((t) => (
              <button
                key={t}
                onClick={() => {
                  setTopic(t);
                  handleCompare(t);
                }}
                className="rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs text-gray-600 hover:border-indigo-300 hover:text-indigo-600 transition-colors dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:border-indigo-600 dark:hover:text-indigo-400"
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Religion selector */}
        <div>
          <label className="mb-1.5 block text-sm font-semibold text-gray-700 dark:text-gray-300">
            Religions to compare{' '}
            <span className="font-normal text-gray-400 dark:text-gray-500">(select 2–6)</span>
          </label>
          <div className="flex flex-wrap gap-2">
            {ALL_RELIGIONS.map((religion) => {
              const color = RELIGION_COLORS[religion];
              const selected = selectedReligions.includes(religion);
              return (
                <button
                  key={religion}
                  onClick={() => toggleReligion(religion)}
                  className={clsx(
                    'flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition-all',
                    selected
                      ? 'border-current text-white shadow-sm'
                      : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:border-gray-600'
                  )}
                  style={selected ? { backgroundColor: color, borderColor: color } : {}}
                >
                  {RELIGION_EMOJI[religion]} {religion}
                </button>
              );
            })}
          </div>
          {selectedReligions.length < 2 && (
            <p className="mt-2 text-xs text-red-500 dark:text-red-400">Select at least 2 religions to compare.</p>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-16 gap-3 text-gray-500 dark:text-gray-400">
          <Loader2 size={20} className="animate-spin" />
          <span>Searching {selectedReligions.length} traditions…</span>
        </div>
      )}

      {/* Results */}
      {result && !loading && (
        <div>
          <h2 className="mb-6 text-center text-xl font-bold text-gray-800 dark:text-gray-200">
            What scriptures say about &ldquo;{result.topic}&rdquo;
          </h2>
          <div
            className="grid gap-6"
            style={{
              gridTemplateColumns: `repeat(${Math.min(selectedReligions.length, 3)}, minmax(0, 1fr))`,
            }}
          >
            {selectedReligions.map((religion) => {
              const verses = result.perspectives[religion] ?? [];
              const color = RELIGION_COLORS[religion];
              return (
                <div
                  key={religion}
                  className="rounded-2xl border-2 bg-white p-5 shadow-sm dark:bg-gray-900"
                  style={{ borderColor: color }}
                >
                  <div className="mb-4 flex items-center gap-2">
                    <span className="text-2xl">{RELIGION_EMOJI[religion]}</span>
                    <h3 className="font-bold text-gray-900 text-lg dark:text-gray-100">{religion}</h3>
                    <span className="ml-auto rounded-full px-2 py-0.5 text-xs font-bold text-white" style={{ backgroundColor: color }}>
                      {verses.length} verses
                    </span>
                  </div>
                  {verses.length === 0 ? (
                    <p className="text-sm text-gray-400 italic dark:text-gray-500">No relevant passages found.</p>
                  ) : (
                    <div className="space-y-3">
                      {verses.map((verse) => (
                        <VerseCard key={verse.id} chunk={verse} />
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
