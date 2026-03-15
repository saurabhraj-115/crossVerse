'use client';

import { useState } from 'react';
import { getEthicsPerspectives } from '@/lib/api';
import {
  type EthicsResponse,
  type Religion,
  ALL_RELIGIONS,
  RELIGION_COLORS,
  RELIGION_EMOJI,
} from '@/lib/types';
import { useSettings } from '@/lib/settings-context';
import VerseCard from '@/components/ui/VerseCard';
import { Flame, Loader2, Search } from 'lucide-react';
import clsx from 'clsx';

const DILEMMAS = [
  'Is it ever moral to lie to protect someone?',
  'Should we prioritize the needs of the many over the few?',
  'Is it ethical to eat animals for food?',
  'Can war ever be just?',
  'Should we forgive someone who never apologizes?',
];

export default function EthicsPage() {
  const { globalReligions } = useSettings();
  const [dilemma, setDilemma] = useState('');
  const [selectedReligions, setSelectedReligions] = useState<Religion[]>(globalReligions);
  const [result, setResult] = useState<EthicsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingMsg, setLoadingMsg] = useState('');
  const [error, setError] = useState<string | null>(null);

  const toggleReligion = (r: Religion) => {
    setSelectedReligions((prev) =>
      prev.includes(r) ? prev.filter((x) => x !== r) : [...prev, r]
    );
  };

  const handleSubmit = async (text: string = dilemma) => {
    if (!text.trim() || selectedReligions.length === 0) return;
    setLoading(true);
    setError(null);
    setResult(null);

    // Cycle through "Consulting…" messages
    const msgs = selectedReligions.map((r) => `Consulting ${r}…`);
    let idx = 0;
    setLoadingMsg(msgs[0]);
    const interval = setInterval(() => {
      idx = (idx + 1) % msgs.length;
      setLoadingMsg(msgs[idx]);
    }, 1200);

    try {
      const data = await getEthicsPerspectives({
        dilemma: text.trim(),
        religions: selectedReligions,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ethics query failed. Please try again.');
    } finally {
      clearInterval(interval);
      setLoading(false);
      setLoadingMsg('');
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-10">
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-full bg-orange-100 text-orange-600 dark:bg-orange-900/40 dark:text-orange-400">
          <Flame size={24} />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Ethical Dilemmas</h1>
        <p className="mt-2 text-gray-500 dark:text-gray-400">
          See how each tradition&apos;s scripture reasons through hard moral questions.
        </p>
      </div>

      {/* Input */}
      <div className="mb-8 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900">
        <div className="mb-4">
          <label className="mb-1.5 block text-sm font-semibold text-gray-700 dark:text-gray-300">Ethical dilemma</label>
          <textarea
            value={dilemma}
            onChange={(e) => setDilemma(e.target.value)}
            placeholder="Describe the dilemma as clearly as you can…"
            rows={3}
            className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500 dark:focus:border-indigo-500"
          />
          <div className="mt-2 flex flex-wrap gap-1.5">
            {DILEMMAS.map((d) => (
              <button
                key={d}
                onClick={() => { setDilemma(d); handleSubmit(d); }}
                className="rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs text-gray-600 hover:border-orange-300 hover:text-orange-600 transition-colors dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:border-orange-600 dark:hover:text-orange-400"
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        {/* Religion multi-select */}
        <div className="mb-4">
          <label className="mb-1.5 block text-sm font-semibold text-gray-700 dark:text-gray-300">Traditions</label>
          <div className="flex flex-wrap gap-2">
            {ALL_RELIGIONS.map((r) => {
              const color = RELIGION_COLORS[r];
              const selected = selectedReligions.includes(r);
              return (
                <button
                  key={r}
                  onClick={() => toggleReligion(r)}
                  className={clsx(
                    'flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition-all',
                    selected
                      ? 'border-current text-white shadow-sm'
                      : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400'
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
          disabled={!dilemma.trim() || selectedReligions.length === 0 || loading}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-orange-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-40 transition-colors"
        >
          {loading ? <Loader2 size={15} className="animate-spin" /> : <Search size={15} />}
          {loading ? loadingMsg : 'Get Perspectives'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Results */}
      {result && !loading && (
        <div>
          <h2 className="mb-6 text-center text-xl font-bold text-gray-800 dark:text-gray-200">
            How traditions reason about: &ldquo;{result.dilemma}&rdquo;
          </h2>
          <div
            className="grid gap-6"
            style={{
              gridTemplateColumns: `repeat(${Math.min(selectedReligions.length, 3)}, minmax(0, 1fr))`,
            }}
          >
            {selectedReligions.map((religion) => {
              const reasoning = result.perspectives[religion] ?? '';
              const sources = result.sources[religion] ?? [];
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
                  </div>
                  <div className="mb-4 prose prose-sm max-w-none text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap text-sm">
                    {reasoning}
                  </div>
                  {sources.length > 0 && (
                    <div className="mt-4 space-y-2">
                      <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">Passages</p>
                      {sources.map((v) => (
                        <VerseCard key={v.id} chunk={v} compact />
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
