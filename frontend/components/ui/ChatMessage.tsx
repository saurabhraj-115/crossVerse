'use client';

import { type ChatMessage as ChatMessageType } from '@/lib/types';
import VerseCard from './VerseCard';
import { BookOpen, User } from 'lucide-react';
import clsx from 'clsx';

interface ChatMessageProps {
  message: ChatMessageType;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div
      className={clsx(
        'flex gap-3 animate-slide-up',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <div
        className={clsx(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white',
          isUser ? 'bg-indigo-600' : 'bg-gradient-to-br from-violet-600 to-indigo-600'
        )}
      >
        {isUser ? <User size={16} /> : <BookOpen size={16} />}
      </div>

      {/* Bubble */}
      <div className={clsx('flex max-w-[85%] flex-col gap-3', isUser && 'items-end')}>
        <div
          className={clsx(
            'rounded-2xl px-4 py-3 text-sm leading-relaxed',
            isUser
              ? 'bg-indigo-600 text-white rounded-tr-sm'
              : 'bg-gray-50 border border-gray-200 text-gray-800 rounded-tl-sm dark:bg-gray-800 dark:border-gray-700 dark:text-gray-200'
          )}
        >
          <p className="whitespace-pre-wrap">
            {isUser
              ? message.content
              : formatAnswerWithCitations(message.content)}
          </p>
        </div>

        {/* Sources */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="w-full space-y-2">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide dark:text-gray-400">
              Sources ({message.sources.length})
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              {message.sources.map((source, i) => (
                <VerseCard key={source.id} chunk={source} index={i + 1} compact />
              ))}
            </div>
          </div>
        )}

        <span className="text-xs text-gray-400 dark:text-gray-500">
          {message.timestamp.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      </div>
    </div>
  );
}

function formatAnswerWithCitations(text: string): React.ReactNode {
  const parts = text.split(/(\[\d+(?:,\s*\d+)*\])/g);
  return parts.map((part, i) => {
    if (/^\[\d+(?:,\s*\d+)*\]$/.test(part)) {
      return (
        <strong key={i} className="font-bold text-indigo-700 dark:text-indigo-400">
          {part}
        </strong>
      );
    }
    return part;
  });
}
