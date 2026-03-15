'use client';

import { useState } from 'react';
import { getSituationWisdom } from '@/lib/api';
import { type SituationResponse, type Religion, ALL_RELIGIONS, RELIGION_COLORS, RELIGION_EMOJI } from '@/lib/types';
import { useSettings } from '@/lib/settings-context';
import VerseCard from '@/components/ui/VerseCard';
import { Heart, Loader2, Send } from 'lucide-react';
import clsx from 'clsx';

const EXAMPLES = [
  "I'm going through a divorce and don't know how to keep going.",
  "I lost my job and feel like I've failed my family.",
  "I'm caring for a dying parent and feel overwhelmed.",
  "I can't forgive someone who deeply hurt me.",
  "I feel completely alone even when surrounded by people.",
];

export default function SituationsPage() {
  const { globalReligions } = useSettings();
  const [situation, setSituation] = useState('');
  const [selectedReligions, setSelectedReligions] = useState<Religion[]>(globalReligions);
  const [result, setResult] = useState<SituationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleReligion = (r: Religion) => {
    setSelectedReligions((prev) =>
      prev.includes(r) ? prev.filter((x) => x !== r) : [...prev, r]
    );
  };

  const handleSubmit = async (text: string = situation) => {
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await getSituationWisdom({
        situation: text.trim(),
        religions: selectedReligions.length > 0 ? selectedReligions : null,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-full bg-rose-100 text-rose-600 dark:bg-rose-900/40 dark:text-rose-400">
          <Heart size={24} />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Life Situations</h1>
        <p className="mt-2 text-gray-500 dark:text-gray-400">
          Describe what you&apos;re going through. Receive honest wisdom from sacred scripture — not preachy, just real.
        </p>
      </div>

      {/* Input */}
      <div className="mb-6 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900">
        <label className="mb-2 block text-sm font-semibold text-gray-700 dark:text-gray-300">
          What are you going through?
        </label>
        <textarea
          value={situation}
          onChange={(e) => setSituation(e.target.value)}
          placeholder="Be as honest as you like. This is just for you…"
          rows={4}
          className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2.5 text-sm text-gray-800 placeholder-gray-400 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500 dark:focus:border-indigo-500"
        />

        {/* Examples */}
        <div className="mt-3">
          <p className="mb-1.5 text-xs text-gray-400 dark:text-gray-500">Examples:</p>
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                onClick={() => {
                  setSituation(ex);
                  handleSubmit(ex);
                }}
                className="rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs text-gray-600 hover:border-rose-300 hover:text-rose-600 transition-colors dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:border-rose-600 dark:hover:text-rose-400"
              >
                {ex.length > 50 ? ex.slice(0, 50) + '…' : ex}
              </button>
            ))}
          </div>
        </div>

        {/* Optional religion filter */}
        <div className="mt-4">
          <label className="mb-1.5 block text-xs font-semibold text-gray-500 dark:text-gray-400">
            Filter by tradition (optional — leave blank for all)
          </label>
          <div className="flex flex-wrap gap-2">
            {ALL_RELIGIONS.map((r) => {
              const color = RELIGION_COLORS[r];
              const selected = selectedReligions.includes(r);
              return (
                <button
                  key={r}
                  onClick={() => toggleReligion(r)}
                  className={clsx(
                    'flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-all',
                    selected
                      ? 'border-current text-white shadow-sm'
                      : 'border-gray-200 bg-white text-gray-500 hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400'
                  )}
                  style={selected ? { backgroundColor: color, borderColor: color } : {}}
                >
                  {RELIGION_EMOJI[r]} {r}
                </button>
              );
            })}
          </div>
        </div>

        <button
          onClick={() => handleSubmit()}
          disabled={!situation.trim() || loading}
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-rose-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-40 transition-colors"
        >
          {loading ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
          {loading ? 'Finding wisdom…' : 'Find Wisdom'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Result */}
      {result && !loading && (
        <div className="space-y-6">
          {/* Wisdom prose */}
          <div className="rounded-2xl border border-rose-100 bg-rose-50 p-6 dark:border-rose-900/40 dark:bg-rose-900/10">
            <p className="text-sm font-semibold uppercase tracking-wider text-rose-600 dark:text-rose-400 mb-3">
              Wisdom from scripture
            </p>
            <div className="prose prose-sm max-w-none text-gray-800 dark:text-gray-200 leading-relaxed whitespace-pre-wrap">
              {result.wisdom}
            </div>
          </div>

          {/* Sources */}
          {result.sources.length > 0 && (
            <div>
              <h3 className="mb-3 text-sm font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                Passages consulted
              </h3>
              <div className="space-y-3">
                {result.sources.map((chunk, i) => (
                  <VerseCard key={chunk.id} chunk={chunk} index={i + 1} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
