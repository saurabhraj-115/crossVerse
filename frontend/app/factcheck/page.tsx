'use client';

import { useState } from 'react';
import { factCheck } from '@/lib/api';
import {
  type FactCheckResponse,
  type FactCheckVerdict,
  type Religion,
  ALL_RELIGIONS,
  RELIGION_EMOJI,
} from '@/lib/types';
import VerseCard from '@/components/ui/VerseCard';
import { CheckCircle2, Loader2, Search } from 'lucide-react';
import clsx from 'clsx';

const VERDICT_CONFIG: Record<FactCheckVerdict, { label: string; bg: string; text: string; border: string }> = {
  supported: {
    label: 'Supported',
    bg: 'bg-green-50 dark:bg-green-900/20',
    text: 'text-green-700 dark:text-green-400',
    border: 'border-green-200 dark:border-green-800',
  },
  contradicted: {
    label: 'Contradicted',
    bg: 'bg-red-50 dark:bg-red-900/20',
    text: 'text-red-700 dark:text-red-400',
    border: 'border-red-200 dark:border-red-800',
  },
  nuanced: {
    label: 'Nuanced',
    bg: 'bg-amber-50 dark:bg-amber-900/20',
    text: 'text-amber-700 dark:text-amber-400',
    border: 'border-amber-200 dark:border-amber-800',
  },
  not_found: {
    label: 'Not Addressed',
    bg: 'bg-gray-50 dark:bg-gray-800',
    text: 'text-gray-600 dark:text-gray-400',
    border: 'border-gray-200 dark:border-gray-700',
  },
};

const EXAMPLE_CLAIMS = [
  { claim: 'Suicide is forbidden', religion: 'Christianity' as Religion },
  { claim: 'Eating pork is prohibited', religion: 'Islam' as Religion },
  { claim: 'Women and men are spiritually equal', religion: 'Sikhism' as Religion },
  { claim: 'The soul is eternal', religion: 'Hinduism' as Religion },
];

export default function FactCheckPage() {
  const [claim, setClaim] = useState('');
  const [religion, setReligion] = useState<Religion>('Christianity');
  const [result, setResult] = useState<FactCheckResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCheck = async (claimText: string = claim, rel: Religion = religion) => {
    if (!claimText.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await factCheck({ claim: claimText.trim(), religion: rel });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fact check failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const verdictCfg = result ? VERDICT_CONFIG[result.verdict] : null;

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100 text-indigo-600 dark:bg-indigo-900/40 dark:text-indigo-400">
          <CheckCircle2 size={24} />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Scripture Fact Check</h1>
        <p className="mt-2 text-gray-500 dark:text-gray-400">
          Verify whether a claim is supported, contradicted, or not addressed by a tradition&apos;s scripture.
        </p>
      </div>

      {/* Input */}
      <div className="mb-6 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900">
        <div className="mb-4">
          <label className="mb-1.5 block text-sm font-semibold text-gray-700 dark:text-gray-300">Claim</label>
          <input
            type="text"
            value={claim}
            onChange={(e) => setClaim(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCheck()}
            placeholder="e.g., Suicide is a sin…"
            className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500 dark:focus:border-indigo-500"
          />
        </div>

        <div className="mb-4">
          <label className="mb-1.5 block text-sm font-semibold text-gray-700 dark:text-gray-300">Tradition</label>
          <div className="grid grid-cols-3 gap-2">
            {ALL_RELIGIONS.map((r) => (
              <button
                key={r}
                onClick={() => setReligion(r)}
                className={clsx(
                  'rounded-lg border px-3 py-2 text-sm font-medium transition-all text-left',
                  religion === r
                    ? 'border-indigo-500 bg-indigo-50 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 dark:border-indigo-600'
                    : 'border-gray-200 text-gray-600 hover:border-gray-300 dark:border-gray-700 dark:text-gray-400 dark:hover:border-gray-600'
                )}
              >
                {RELIGION_EMOJI[r]} {r}
              </button>
            ))}
          </div>
        </div>

        {/* Examples */}
        <div className="mb-4">
          <p className="mb-1.5 text-xs text-gray-400 dark:text-gray-500">Quick examples:</p>
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLE_CLAIMS.map(({ claim: c, religion: r }) => (
              <button
                key={c + r}
                onClick={() => {
                  setClaim(c);
                  setReligion(r);
                  handleCheck(c, r);
                }}
                className="rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs text-gray-600 hover:border-indigo-300 hover:text-indigo-600 transition-colors dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:border-indigo-600 dark:hover:text-indigo-400"
              >
                &ldquo;{c}&rdquo; — {r}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={() => handleCheck()}
          disabled={!claim.trim() || loading}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40 transition-colors"
        >
          {loading ? <Loader2 size={15} className="animate-spin" /> : <Search size={15} />}
          {loading ? 'Checking…' : 'Check Claim'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Result */}
      {result && !loading && verdictCfg && (
        <div className="space-y-6">
          {/* Verdict badge */}
          <div className={clsx('rounded-2xl border p-6', verdictCfg.bg, verdictCfg.border)}>
            <div className="mb-3 flex items-center gap-3">
              <span
                className={clsx(
                  'inline-flex rounded-full px-4 py-1 text-sm font-bold',
                  verdictCfg.bg,
                  verdictCfg.text,
                  'border',
                  verdictCfg.border
                )}
              >
                {verdictCfg.label}
              </span>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {RELIGION_EMOJI[result.religion as Religion]} {result.religion} scripture
              </span>
            </div>
            <p className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
              Claim: &ldquo;{result.claim}&rdquo;
            </p>
            <div className="prose prose-sm max-w-none text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
              {result.explanation}
            </div>
          </div>

          {/* Sources */}
          {result.sources.length > 0 && (
            <div>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
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
