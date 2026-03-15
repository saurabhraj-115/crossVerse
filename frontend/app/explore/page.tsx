'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getTopics } from '@/lib/api';
import type { TopicsResponse } from '@/lib/types';
import { Compass, Loader2, ExternalLink } from 'lucide-react';

export default function ExplorePage() {
  const [topics, setTopics] = useState<TopicsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getTopics()
      .then(setTopics)
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Failed to load topics')
      )
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-900/40 dark:text-emerald-400">
          <Compass size={24} />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Topic Explorer</h1>
        <p className="mt-2 text-gray-500 dark:text-gray-400">
          Browse curated topics and see what all six traditions say. Click any topic to compare.
        </p>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-16 gap-3 text-gray-500 dark:text-gray-400">
          <Loader2 size={20} className="animate-spin" />
          <span>Loading topics…</span>
        </div>
      )}

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-900/20 dark:text-red-400">
          {error} — Make sure the backend is running.
        </div>
      )}

      {topics && (
        <div className="space-y-8">
          {topics.categories.map((category) => (
            <div key={category.name}>
              <h2 className="mb-4 text-lg font-bold text-gray-800 dark:text-gray-200">{category.name}</h2>
              <div className="flex flex-wrap gap-3">
                {category.topics.map((topic) => (
                  <div key={topic} className="group relative">
                    <Link
                      href={`/compare?topic=${encodeURIComponent(topic)}`}
                      className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-gray-700 shadow-sm hover:border-emerald-300 hover:text-emerald-700 hover:shadow-md transition-all dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:border-emerald-700 dark:hover:text-emerald-400 dark:shadow-none"
                    >
                      {topic}
                      <ExternalLink size={12} className="opacity-0 group-hover:opacity-100 transition-opacity" />
                    </Link>
                    {/* Hover actions */}
                    <div className="absolute top-full left-0 mt-1.5 hidden group-hover:flex gap-1 z-10 bg-white border border-gray-200 rounded-lg shadow-lg p-1 text-xs whitespace-nowrap dark:bg-gray-800 dark:border-gray-700">
                      <Link
                        href={`/compare?topic=${encodeURIComponent(topic)}`}
                        className="rounded-md px-2 py-1 hover:bg-emerald-50 text-emerald-700 font-medium dark:hover:bg-emerald-900/30 dark:text-emerald-400"
                      >
                        Compare
                      </Link>
                      <Link
                        href={`/debate?question=${encodeURIComponent(`What do scriptures say about ${topic}?`)}`}
                        className="rounded-md px-2 py-1 hover:bg-rose-50 text-rose-700 font-medium dark:hover:bg-rose-900/30 dark:text-rose-400"
                      >
                        Debate
                      </Link>
                      <Link
                        href={`/query?q=${encodeURIComponent(`What do scriptures say about ${topic}?`)}`}
                        className="rounded-md px-2 py-1 hover:bg-indigo-50 text-indigo-700 font-medium dark:hover:bg-indigo-900/30 dark:text-indigo-400"
                      >
                        Ask
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* How to use */}
      <div className="mt-12 rounded-2xl border border-gray-200 bg-gray-50 p-6 dark:border-gray-700 dark:bg-gray-800">
        <h3 className="mb-3 font-bold text-gray-800 dark:text-gray-200">How to use the Explorer</h3>
        <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
          <li className="flex items-start gap-2">
            <span className="mt-0.5 text-emerald-500">•</span>
            <span><strong>Compare</strong> — See relevant verses from all 6 traditions side-by-side for this topic</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-0.5 text-rose-500">•</span>
            <span><strong>Debate</strong> — Each tradition's scriptures respond to the question independently</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-0.5 text-indigo-500">•</span>
            <span><strong>Ask</strong> — Get a synthesized answer drawing from all traditions at once</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
