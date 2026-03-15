'use client';

import { useState } from 'react';
import { RELIGION_COLORS, type Religion, type ScriptureChunk } from '@/lib/types';
import ReligionBadge from './ReligionBadge';
import { BookOpen, ChevronDown, ChevronUp } from 'lucide-react';

interface VerseCardProps {
  chunk: ScriptureChunk;
  index?: number;
  compact?: boolean;
}

export default function VerseCard({ chunk, index, compact = false }: VerseCardProps) {
  const borderColor = RELIGION_COLORS[chunk.religion as Religion] ?? '#6B7280';
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="rounded-xl border-l-4 bg-white p-4 shadow-sm transition-shadow hover:shadow-md dark:bg-gray-800 dark:shadow-none dark:hover:shadow-none"
      style={{ borderLeftColor: borderColor }}
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          {index !== undefined && (
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-gray-100 text-xs font-bold text-gray-500 dark:bg-gray-700 dark:text-gray-400">
              {index}
            </span>
          )}
          <ReligionBadge religion={chunk.religion} size="sm" />
          <span className="flex items-center gap-1 text-xs font-semibold text-gray-600 dark:text-gray-400">
            <BookOpen size={12} />
            {chunk.reference}
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {chunk.score !== undefined && chunk.score !== null && (
            <span className="text-xs text-gray-400 dark:text-gray-500">
              {(chunk.score * 100).toFixed(0)}% match
            </span>
          )}
          <button
            onClick={() => setExpanded((e) => !e)}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            title={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
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
