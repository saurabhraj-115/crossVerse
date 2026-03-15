'use client';

import { useState, useRef, useEffect } from 'react';
import { queryScriptures } from '@/lib/api';
import {
  type ChatMessage,
  type Religion,
  type QueryMode,
  ALL_RELIGIONS,
  RELIGION_EMOJI,
} from '@/lib/types';
import ChatMessageComponent from '@/components/ui/ChatMessage';
import { Send, Loader2, GraduationCap, MessageCircle } from 'lucide-react';
import clsx from 'clsx';

const QUICK_QUESTIONS = [
  'What is the nature of the soul?',
  'How should we treat our enemies?',
  'What happens after death?',
  'What does scripture say about forgiveness?',
  'How should we approach prayer?',
];

export default function QueryChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<QueryMode>('simple');
  const [selectedReligions, setSelectedReligions] = useState<Religion[]>([]);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const toggleReligion = (religion: Religion) => {
    setSelectedReligions((prev) =>
      prev.includes(religion) ? prev.filter((r) => r !== religion) : [...prev, religion]
    );
  };

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const response = await queryScriptures({
        question: text.trim(),
        religions: selectedReligions.length > 0 ? selectedReligions : null,
        mode,
      });

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Controls bar */}
      <div className="border-b border-gray-200 bg-white px-4 py-3">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-4">
          {/* Mode toggle */}
          <div className="flex items-center gap-1 rounded-lg bg-gray-100 p-1">
            <button
              onClick={() => setMode('simple')}
              className={clsx(
                'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                mode === 'simple'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              )}
            >
              <MessageCircle size={13} />
              Simple
            </button>
            <button
              onClick={() => setMode('scholar')}
              className={clsx(
                'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                mode === 'scholar'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              )}
            >
              <GraduationCap size={13} />
              Scholar
            </button>
          </div>

          {/* Religion filters */}
          <div className="flex flex-wrap gap-1">
            {ALL_RELIGIONS.map((religion) => (
              <button
                key={religion}
                onClick={() => toggleReligion(religion)}
                className={clsx(
                  'rounded-full border px-2 py-0.5 text-xs font-medium transition-colors',
                  selectedReligions.includes(religion)
                    ? 'border-indigo-400 bg-indigo-50 text-indigo-700'
                    : 'border-gray-200 bg-white text-gray-500 hover:border-gray-300'
                )}
              >
                {RELIGION_EMOJI[religion]} {religion}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-3xl space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="mb-4 text-4xl">📖</div>
              <h2 className="mb-2 text-xl font-bold text-gray-800">
                Ask the Scriptures
              </h2>
              <p className="mb-6 max-w-md text-sm text-gray-500">
                Ask any question and receive answers grounded exclusively in sacred
                scripture from across traditions. All citations included.
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {QUICK_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    onClick={() => sendMessage(q)}
                    className="rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-600 hover:border-indigo-300 hover:text-indigo-600 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message, i) => (
            <ChatMessageComponent key={i} message={message} />
          ))}

          {loading && (
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-violet-600 to-indigo-600 text-white">
                <Loader2 size={16} className="animate-spin" />
              </div>
              <div className="rounded-2xl bg-gray-50 border border-gray-200 px-4 py-3">
                <div className="flex gap-1">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.3s]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.15s]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400" />
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 bg-white px-4 py-4">
        <form onSubmit={handleSubmit} className="mx-auto max-w-3xl">
          <div className="flex items-end gap-3 rounded-xl border border-gray-300 bg-white p-2 shadow-sm focus-within:border-indigo-400 focus-within:ring-1 focus-within:ring-indigo-400 transition-all">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about scripture… (Enter to send, Shift+Enter for new line)"
              rows={1}
              className="flex-1 resize-none bg-transparent px-2 py-1 text-sm text-gray-900 placeholder-gray-400 outline-none"
              style={{ maxHeight: '120px' }}
              disabled={loading}
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Send size={15} />
            </button>
          </div>
          <p className="mt-2 text-center text-xs text-gray-400">
            Answers are grounded exclusively in scripture. Always cite primary sources.
          </p>
        </form>
      </div>
    </div>
  );
}
