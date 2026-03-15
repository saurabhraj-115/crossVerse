'use client';

import { type ScriptureChunk } from '@/lib/types';
import VerseCard from './VerseCard';
import { ChevronDown, ChevronUp, Library } from 'lucide-react';
import { useState } from 'react';

interface CitationTrailProps {
  sources: ScriptureChunk[];
  label?: string;
}

export default function CitationTrail({
  sources,
  label = 'Retrieved Scripture Passages',
}: CitationTrailProps) {
  const [expanded, setExpanded] = useState(false);

  if (!sources.length) return null;

  const preview = sources.slice(0, 2);
  const rest = sources.slice(2);

  return (
    <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between text-left"
      >
        <div className="flex items-center gap-2">
          <Library size={16} className="text-indigo-500" />
          <span className="text-sm font-semibold text-gray-700">{label}</span>
          <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-bold text-indigo-700">
            {sources.length}
          </span>
        </div>
        {expanded ? (
          <ChevronUp size={16} className="text-gray-400" />
        ) : (
          <ChevronDown size={16} className="text-gray-400" />
        )}
      </button>

      <div className="mt-3 space-y-2">
        {preview.map((source, i) => (
          <VerseCard key={source.id} chunk={source} index={i + 1} />
        ))}
      </div>

      {rest.length > 0 && expanded && (
        <div className="mt-2 space-y-2">
          {rest.map((source, i) => (
            <VerseCard key={source.id} chunk={source} index={preview.length + i + 1} />
          ))}
        </div>
      )}

      {rest.length > 0 && !expanded && (
        <button
          onClick={() => setExpanded(true)}
          className="mt-2 text-xs text-indigo-600 hover:underline"
        >
          + {rest.length} more passages
        </button>
      )}
    </div>
  );
}
