'use client';

import { RELIGION_COLORS, type Religion, type ScriptureChunk } from '@/lib/types';
import ReligionBadge from './ReligionBadge';
import { BookOpen } from 'lucide-react';

interface VerseCardProps {
  chunk: ScriptureChunk;
  index?: number;
  compact?: boolean;
}

export default function VerseCard({ chunk, index, compact = false }: VerseCardProps) {
  const borderColor = RELIGION_COLORS[chunk.religion as Religion] ?? '#6B7280';

  return (
    <div
      className="rounded-xl border-l-4 bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
      style={{ borderLeftColor: borderColor }}
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          {index !== undefined && (
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-gray-100 text-xs font-bold text-gray-500">
              {index}
            </span>
          )}
          <ReligionBadge religion={chunk.religion} size="sm" />
          <span className="flex items-center gap-1 text-xs font-semibold text-gray-600">
            <BookOpen size={12} />
            {chunk.reference}
          </span>
        </div>
        {chunk.score !== undefined && chunk.score !== null && (
          <span className="shrink-0 text-xs text-gray-400">
            {(chunk.score * 100).toFixed(0)}% match
          </span>
        )}
      </div>

      {!compact && (
        <p className="mt-2 text-sm leading-relaxed text-gray-700 italic">
          &ldquo;{chunk.text}&rdquo;
        </p>
      )}

      {compact && (
        <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-gray-600 italic">
          &ldquo;{chunk.text}&rdquo;
        </p>
      )}

      <p className="mt-2 text-xs text-gray-400">{chunk.translation}</p>
    </div>
  );
}
