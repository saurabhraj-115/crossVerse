'use client';

import { useState } from 'react';
import { debateReligions } from '@/lib/api';
import {
  type DebateResponse,
  type Religion,
  ALL_RELIGIONS,
  RELIGION_COLORS,
  RELIGION_EMOJI,
} from '@/lib/types';
import { useSettings } from '@/lib/settings-context';
import VerseCard from '@/components/ui/VerseCard';
import { Swords, Loader2, Play } from 'lucide-react';
import clsx from 'clsx';

const DEBATE_QUESTIONS = [
  'Is violence ever justified?',
  'What is the path to salvation or liberation?',
  'How should we treat non-believers?',
  'What is the role of suffering in spiritual growth?',
  'Is there free will, or is everything predestined?',
];

export default function DebateView() {
  const { globalReligions } = useSettings();
  const [question, setQuestion] = useState('');
  const [selectedReligions, setSelectedReligions] = useState<Religion[]>(globalReligions);
  const [result, setResult] = useState<DebateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleReligion = (religion: Religion) => {
    setSelectedReligions((prev) =>
      prev.includes(religion) ? prev.filter((r) => r !== religion) : [...prev, religion]
    );
  };

  const handleDebate = async (q: string = question) => {
    if (!q.trim() || selectedReligions.length < 2) return;
    setLoading(true);
    setError(null);
    try {
      const data = await debateReligions({
        question: q.trim(),
        religions: selectedReligions,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Debate failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-full bg-rose-100 text-rose-600 dark:bg-rose-900/40 dark:text-rose-400">
          <Swords size={24} />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Scripture Debate</h1>
        <p className="mt-2 text-gray-500 dark:text-gray-400">
          Each tradition&apos;s scriptures respond to the same question. No commentary — only text.
        </p>
      </div>

      {/* Controls */}
      <div className="mb-8 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900">
        <div className="mb-5">
          <label className="mb-1.5 block text-sm font-semibold text-gray-700 dark:text-gray-300">Question</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleDebate()}
              placeholder="Pose a question for the traditions to answer…"
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-rose-400 focus:outline-none focus:ring-1 focus:ring-rose-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500 dark:focus:border-rose-500"
            />
            <button
              onClick={() => handleDebate()}
              disabled={!question.trim() || selectedReligions.length < 2 || loading}
              className="flex items-center gap-2 rounded-lg bg-rose-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-40 transition-colors"
            >
              {loading ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
              Debate
            </button>
          </div>

          <div className="mt-3 flex flex-wrap gap-1.5">
            {DEBATE_QUESTIONS.map((q) => (
              <button
                key={q}
                onClick={() => {
                  setQuestion(q);
                  handleDebate(q);
                }}
                className="rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs text-gray-600 hover:border-rose-300 hover:text-rose-600 transition-colors dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:border-rose-700 dark:hover:text-rose-400"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-semibold text-gray-700 dark:text-gray-300">
            Debating traditions{' '}
            <span className="font-normal text-gray-400 dark:text-gray-500">(select 2+)</span>
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
        </div>
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {loading && (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-gray-500 dark:text-gray-400">
          <Loader2 size={24} className="animate-spin text-rose-500" />
          <span>Consulting {selectedReligions.length} traditions…</span>
        </div>
      )}

      {result && !loading && (
        <div className="space-y-8">
          <div className="text-center">
            <h2 className="text-xl font-bold text-gray-800 dark:text-gray-200">
              &ldquo;{result.question}&rdquo;
            </h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Each tradition speaks for itself</p>
          </div>

          <div className="space-y-6">
            {selectedReligions.map((religion, idx) => {
              const response = result.responses[religion];
              const color = RELIGION_COLORS[religion];
              if (!response) return null;

              return (
                <div key={religion} className="rounded-2xl border border-gray-200 bg-white shadow-sm overflow-hidden dark:border-gray-700 dark:bg-gray-900">
                  {/* Religion header */}
                  <div
                    className="px-6 py-4 text-white"
                    style={{ backgroundColor: color }}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-3xl">{RELIGION_EMOJI[religion]}</span>
                      <div>
                        <h3 className="text-lg font-bold">{religion}</h3>
                        <p className="text-sm opacity-80">
                          {response.sources.length} scripture passages cited
                        </p>
                      </div>
                      <span className="ml-auto rounded-full bg-white/20 px-3 py-1 text-xs font-bold">
                        Position {idx + 1}
                      </span>
                    </div>
                  </div>

                  <div className="px-6 py-5">
                    {/* Answer */}
                    <div className="mb-5 rounded-xl bg-gray-50 p-4 dark:bg-gray-800">
                      <p className="text-sm leading-relaxed text-gray-700 whitespace-pre-wrap dark:text-gray-300">
                        {response.answer}
                      </p>
                    </div>

                    {/* Source verses */}
                    {response.sources.length > 0 && (
                      <div>
                        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                          Supporting Passages
                        </p>
                        <div className="grid gap-3 sm:grid-cols-2">
                          {response.sources.map((source, i) => (
                            <VerseCard key={source.id} chunk={source} index={i + 1} />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
