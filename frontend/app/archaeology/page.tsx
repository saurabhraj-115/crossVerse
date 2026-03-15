'use client';

import { useState } from 'react';
import { archaeologyConcept } from '@/lib/api';
import {
  type ArchaeologyResponse,
  type Religion,
  RELIGION_COLORS,
  RELIGION_EMOJI,
} from '@/lib/types';
import VerseCard from '@/components/ui/VerseCard';
import { Microscope, Loader2, Search } from 'lucide-react';

const CONCEPTS = [
  'compassion', 'prayer', 'sin', 'enlightenment', 'justice', 'love', 'forgiveness', 'soul',
];

export default function ArchaeologyPage() {
  const [concept, setConcept] = useState('');
  const [result, setResult] = useState<ArchaeologyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (c: string = concept) => {
    if (!c.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await archaeologyConcept({ concept: c.trim() });
      if (!data || !data.analysis) {
        setError('No result returned. Please try again.');
      } else {
        setResult(data);
      }
    } catch (err) {
      setError(err instanceof Error && err.message ? err.message : 'Archaeology query failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Group sources by religion
  const grouped = result
    ? result.sources.reduce<Record<string, typeof result.sources>>((acc, chunk) => {
        const rel = chunk.religion;
        if (!acc[rel]) acc[rel] = [];
        acc[rel].push(chunk);
        return acc;
      }, {})
    : {};

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-full bg-stone-100 text-stone-600 dark:bg-stone-900/40 dark:text-stone-400">
          <Microscope size={24} />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Concept Archaeology</h1>
        <p className="mt-2 text-gray-500 dark:text-gray-400">
          Trace how a concept developed across all six sacred traditions. Discover shared roots and divergences.
        </p>
      </div>

      {/* Input */}
      <div className="mb-8 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900">
        <label className="mb-1.5 block text-sm font-semibold text-gray-700 dark:text-gray-300">Concept to trace</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={concept}
            onChange={(e) => setConcept(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="e.g., compassion, prayer, justice…"
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500 dark:focus:border-indigo-500"
          />
          <button
            onClick={() => handleSearch()}
            disabled={!concept.trim() || loading}
            className="flex items-center gap-2 rounded-lg bg-stone-700 px-4 py-2.5 text-sm font-medium text-white hover:bg-stone-800 disabled:cursor-not-allowed disabled:opacity-40 transition-colors dark:bg-stone-600 dark:hover:bg-stone-500"
          >
            {loading ? <Loader2 size={15} className="animate-spin" /> : <Search size={15} />}
            {loading ? 'Tracing…' : 'Trace'}
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {CONCEPTS.map((c) => (
            <button
              key={c}
              onClick={() => { setConcept(c); handleSearch(c); }}
              className="rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs text-gray-600 hover:border-stone-400 hover:text-stone-700 transition-colors dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:border-stone-500 dark:hover:text-stone-300"
            >
              {c}
            </button>
          ))}
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
        <div className="flex items-center justify-center py-20 gap-3 text-gray-500 dark:text-gray-400">
          <Loader2 size={24} className="animate-spin" />
          <span>Tracing concept across traditions…</span>
        </div>
      )}

      {/* Result */}
      {result && !loading && (
        <div className="space-y-8">
          {/* Analysis */}
          <div className="rounded-2xl border border-stone-200 bg-stone-50 p-8 dark:border-stone-800 dark:bg-stone-900/30">
            <h2 className="mb-4 text-xl font-bold text-gray-900 dark:text-gray-100 capitalize">
              &ldquo;{result.concept}&rdquo; across traditions
            </h2>
            <div className="prose prose-sm max-w-none text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
              {result.analysis}
            </div>
          </div>

          {/* Sources — timeline-ish layout grouped by religion */}
          {Object.keys(grouped).length > 0 && (
            <div>
              <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Source passages by tradition
              </h3>
              <div className="space-y-6">
                {Object.entries(grouped).map(([religion, verses]) => {
                  const color = RELIGION_COLORS[religion as Religion] ?? '#6B7280';
                  return (
                    <div key={religion} className="flex gap-4">
                      {/* Timeline dot + line */}
                      <div className="flex flex-col items-center">
                        <div
                          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xl"
                          style={{ backgroundColor: `${color}22`, border: `2px solid ${color}` }}
                        >
                          {RELIGION_EMOJI[religion as Religion]}
                        </div>
                        <div className="mt-2 flex-1 w-0.5" style={{ backgroundColor: `${color}44` }} />
                      </div>
                      {/* Verses */}
                      <div className="flex-1 pb-4">
                        <h4 className="mb-2 font-bold text-gray-800 dark:text-gray-200">{religion}</h4>
                        <div className="space-y-2">
                          {verses.map((v) => (
                            <VerseCard key={v.id} chunk={v} compact />
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
