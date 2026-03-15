'use client';

import { useState } from 'react';
import { RELIGION_COLORS, type Religion, type ScriptureChunk } from '@/lib/types';
import ReligionBadge from './ReligionBadge';
import { BookOpen, ChevronDown, ChevronUp, Quote, Share2, Copy, Check } from 'lucide-react';

interface VerseCardProps {
  chunk: ScriptureChunk;
  index?: number;
  compact?: boolean;
}

function CitationPopover({ chunk, onClose }: { chunk: ScriptureChunk; onClose: () => void }) {
  const [copied, setCopied] = useState<string | null>(null);

  const year = new Date().getFullYear();

  const chicago = `"${chunk.reference}." ${chunk.translation}. ${chunk.book}${chunk.chapter ? `, chap. ${chunk.chapter}` : ''}.`;
  const mla = `"${chunk.reference}." *${chunk.translation}*. ${chunk.book}${chunk.chapter ? ` ${chunk.chapter}` : ''}, ${chunk.verse ? `v. ${chunk.verse}` : ''}.`;
  const sbl = `${chunk.book} ${chunk.chapter ?? ''}${chunk.verse ? ':' + chunk.verse : ''} (${chunk.translation}).`;

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div className="absolute right-0 top-8 z-50 w-80 rounded-xl border border-gray-200 bg-white p-4 shadow-xl dark:border-gray-700 dark:bg-gray-900">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm font-bold text-gray-800 dark:text-gray-200">Citation Formats</span>
        <button onClick={onClose} className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">✕</button>
      </div>
      {[
        { label: 'Chicago', text: chicago },
        { label: 'MLA', text: mla },
        { label: 'SBL', text: sbl },
      ].map(({ label, text }) => (
        <div key={label} className="mb-3">
          <div className="mb-1 flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 dark:text-gray-400">{label}</span>
            <button
              onClick={() => handleCopy(text, label)}
              className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-300"
            >
              {copied === label ? <Check size={11} /> : <Copy size={11} />}
              {copied === label ? 'Copied' : 'Copy'}
            </button>
          </div>
          <p className="rounded bg-gray-50 p-2 text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-300 font-mono leading-relaxed">
            {text}
          </p>
        </div>
      ))}
    </div>
  );
}

export default function VerseCard({ chunk, index, compact = false }: VerseCardProps) {
  const borderColor = RELIGION_COLORS[chunk.religion as Religion] ?? '#6B7280';
  const [expanded, setExpanded] = useState(false);
  const [showCite, setShowCite] = useState(false);
  const [shareStatus, setShareStatus] = useState<'idle' | 'copied'>('idle');

  const handleShare = async () => {
    const title = `${chunk.reference} — CrossVerse`;
    const text = `"${chunk.text}"\n\n— ${chunk.reference} (${chunk.translation})`;
    const url = typeof window !== 'undefined' ? window.location.href : 'https://crossverse.app';

    if (typeof navigator !== 'undefined' && navigator.share) {
      try {
        await navigator.share({ title, text, url });
        return;
      } catch {
        // User cancelled or share failed — fall through to clipboard
      }
    }

    // Fallback: copy to clipboard
    navigator.clipboard.writeText(`${text}\n\nvia CrossVerse: ${url}`);
    setShareStatus('copied');
    setTimeout(() => setShareStatus('idle'), 2000);
  };

  return (
    <div
      className="relative rounded-xl border-l-4 bg-white p-4 shadow-sm transition-shadow hover:shadow-md dark:bg-gray-800 dark:shadow-none dark:hover:shadow-none"
      style={{ borderLeftColor: borderColor }}
    >
      {/* Header row: religion badge + reference on left, actions on right */}
      <div className="mb-2 flex items-center justify-between gap-2 min-w-0">
        <div className="flex items-center gap-1.5 min-w-0 overflow-hidden">
          {index !== undefined && (
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gray-100 text-xs font-bold text-gray-500 dark:bg-gray-700 dark:text-gray-400">
              {index}
            </span>
          )}
          <ReligionBadge religion={chunk.religion} size="sm" />
        </div>

        {/* Actions: always shrink-0 so they never overflow */}
        <div className="flex items-center gap-1 shrink-0">
          {chunk.score !== undefined && chunk.score !== null && (
            <span className="text-xs text-gray-400 dark:text-gray-500 tabular-nums">
              {(chunk.score * 100).toFixed(0)}%
            </span>
          )}

          <button
            onClick={handleShare}
            className="flex h-6 w-6 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300 transition-colors"
            title={shareStatus === 'copied' ? 'Copied!' : 'Copy shareable text'}
          >
            {shareStatus === 'copied' ? <Check size={12} className="text-green-500" /> : <Share2 size={12} />}
          </button>

          <div className="relative">
            <button
              onClick={() => setShowCite((v) => !v)}
              className="flex h-6 w-6 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300 transition-colors"
              title="Citation formats"
            >
              <Quote size={12} />
            </button>
            {showCite && (
              <CitationPopover chunk={chunk} onClose={() => setShowCite(false)} />
            )}
          </div>

          <button
            onClick={() => setExpanded((e) => !e)}
            className="flex h-6 w-6 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            title={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
        </div>
      </div>

      {/* Reference on its own line so it never fights for space */}
      <div className="mb-1 flex items-center gap-1 text-xs font-semibold text-gray-600 dark:text-gray-400">
        <BookOpen size={11} className="shrink-0" />
        <span className="truncate">{chunk.reference}</span>
      </div>

      {/* Collapsed: always show a preview */}
      {!expanded && (
        <p
          className={`mt-1 leading-relaxed text-gray-700 italic dark:text-gray-300 cursor-pointer ${
            compact ? 'line-clamp-2 text-xs' : 'line-clamp-3 text-sm'
          }`}
          onClick={() => setExpanded(true)}
        >
          &ldquo;{chunk.text}&rdquo;
        </p>
      )}

      {/* Expanded: full text highlighted */}
      {expanded && (
        <div
          className="mt-2 rounded-lg p-3 cursor-pointer"
          style={{ backgroundColor: `${borderColor}15` }}
          onClick={() => setExpanded(false)}
        >
          <p className="text-sm leading-relaxed text-gray-800 italic dark:text-gray-200 whitespace-pre-wrap">
            &ldquo;{chunk.text}&rdquo;
          </p>
          {chunk.book && (
            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              {chunk.book}{chunk.chapter ? `, Chapter ${chunk.chapter}` : ''}{chunk.verse ? `, Verse ${chunk.verse}` : ''}
            </p>
          )}
        </div>
      )}

      <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">{chunk.translation}</p>
    </div>
  );
}
