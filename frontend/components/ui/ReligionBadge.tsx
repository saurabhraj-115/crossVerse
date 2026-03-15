'use client';

import { RELIGION_BG, RELIGION_EMOJI, type Religion } from '@/lib/types';
import clsx from 'clsx';

interface ReligionBadgeProps {
  religion: Religion | string;
  size?: 'sm' | 'md';
  showEmoji?: boolean;
}

export default function ReligionBadge({
  religion,
  size = 'md',
  showEmoji = true,
}: ReligionBadgeProps) {
  const bgClass =
    RELIGION_BG[religion as Religion] ??
    'bg-gray-100 text-gray-700 border-gray-200';
  const emoji = showEmoji ? (RELIGION_EMOJI[religion as Religion] ?? '📖') : '';

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 rounded-full border font-medium',
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm',
        bgClass
      )}
    >
      {showEmoji && <span>{emoji}</span>}
      {religion}
    </span>
  );
}
