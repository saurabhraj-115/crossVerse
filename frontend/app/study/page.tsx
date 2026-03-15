'use client';

import { useState } from 'react';
import { generateStudyPlan } from '@/lib/api';
import {
  type StudyResponse,
  type StudyDay,
  type Religion,
  ALL_RELIGIONS,
  RELIGION_COLORS,
  RELIGION_EMOJI,
} from '@/lib/types';
import { useSettings } from '@/lib/settings-context';
import VerseCard from '@/components/ui/VerseCard';
import { GraduationCap, Loader2, ChevronDown, ChevronUp, BookOpen } from 'lucide-react';
import clsx from 'clsx';

const TOPICS = [
  'Faith and doubt', 'Love and compassion', 'Death and afterlife',
  'Prayer and meditation', 'Justice and mercy', 'The ego and the self',
];

const DAY_OPTIONS = [3, 7, 14];

export default function StudyPage() {
  const { globalReligions } = useSettings();
  const [topic, setTopic] = useState('');
  const [days, setDays] = useState(7);
  const [selectedReligions, setSelectedReligions] = useState<Religion[]>(globalReligions);
  const [result, setResult] = useState<StudyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openDay, setOpenDay] = useState<number | null>(1);

  const toggleReligion = (r: Religion) => {
    setSelectedReligions((prev) =>
      prev.includes(r) ? prev.filter((x) => x !== r) : [...prev, r]
    );
  };

  const handleStart = async (t: string = topic) => {
    if (!t.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setOpenDay(1);
    try {
      const data = await generateStudyPlan({
        topic: t.trim(),
        days,
        religions: selectedReligions.length > 0 ? selectedReligions : null,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Study plan generation failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-full bg-teal-100 text-teal-600 dark:bg-teal-900/40 dark:text-teal-400">
          <GraduationCap size={24} />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Scripture Study Plans</h1>
        <p className="mt-2 text-gray-500 dark:text-gray-400">
          Generate a structured multi-day curriculum comparing how all traditions approach a topic.
        </p>
      </div>

      {/* Input */}
      <div className="mb-8 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900">
        <div className="mb-4">
          <label className="mb-1.5 block text-sm font-semibold text-gray-700 dark:text-gray-300">Topic</label>
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleStart()}
            placeholder="e.g., prayer and meditation…"
            className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500 dark:focus:border-indigo-500"
          />
          <div className="mt-2 flex flex-wrap gap-1.5">
            {TOPICS.map((t) => (
              <button
                key={t}
                onClick={() => { setTopic(t); handleStart(t); }}
                className="rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs text-gray-600 hover:border-teal-300 hover:text-teal-600 transition-colors dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:border-teal-600 dark:hover:text-teal-400"
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Day count */}
        <div className="mb-4">
          <label className="mb-1.5 block text-sm font-semibold text-gray-700 dark:text-gray-300">Duration</label>
          <div className="flex gap-2">
            {DAY_OPTIONS.map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={clsx(
                  'rounded-lg border px-4 py-2 text-sm font-medium transition-all',
                  days === d
                    ? 'border-teal-500 bg-teal-50 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300 dark:border-teal-600'
                    : 'border-gray-200 text-gray-600 hover:border-gray-300 dark:border-gray-700 dark:text-gray-400'
                )}
              >
                {d} days
              </button>
            ))}
          </div>
        </div>

        {/* Religion filter */}
        <div className="mb-4">
          <label className="mb-1.5 block text-sm font-semibold text-gray-700 dark:text-gray-300">Traditions</label>
          <div className="flex flex-wrap gap-2">
            {ALL_RELIGIONS.map((r) => {
              const color = RELIGION_COLORS[r];
              const selected = selectedReligions.includes(r);
              return (
                <button
                  key={r}
                  onClick={() => toggleReligion(r)}
                  className={clsx(
                    'flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-all',
                    selected
                      ? 'border-current text-white shadow-sm'
                      : 'border-gray-200 bg-white text-gray-500 hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400'
                  )}
                  style={selected ? { backgroundColor: color, borderColor: color } : {}}
                >
                  {RELIGION_EMOJI[r]} {r}
                </button>
              );
            })}
          </div>
        </div>

        <button
          onClick={() => handleStart()}
          disabled={!topic.trim() || loading}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-teal-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-40 transition-colors"
        >
          {loading ? <Loader2 size={15} className="animate-spin" /> : <BookOpen size={15} />}
          {loading ? 'Generating curriculum…' : 'Start Study'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Result — accordion */}
      {result && !loading && (
        <div>
          <h2 className="mb-4 text-xl font-bold text-gray-800 dark:text-gray-200">
            {days}-Day Study Plan: &ldquo;{result.topic}&rdquo;
          </h2>
          <div className="space-y-3">
            {result.days.map((day) => (
              <DayAccordion
                key={day.day}
                day={day}
                isOpen={openDay === day.day}
                onToggle={() => setOpenDay(openDay === day.day ? null : day.day)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function DayAccordion({
  day,
  isOpen,
  onToggle,
}: {
  day: StudyDay;
  isOpen: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between px-5 py-4 text-left hover:bg-gray-50 transition-colors dark:hover:bg-gray-800"
      >
        <div className="flex items-center gap-3">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-teal-100 text-sm font-bold text-teal-700 dark:bg-teal-900/40 dark:text-teal-400">
            {day.day}
          </span>
          <div>
            <div className="font-semibold text-gray-900 dark:text-gray-100">{day.theme}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">{day.verses.length} verse{day.verses.length !== 1 ? 's' : ''}</div>
          </div>
        </div>
        {isOpen ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
      </button>

      {isOpen && (
        <div className="border-t border-gray-100 px-5 py-4 dark:border-gray-700">
          {/* Reflection prompt */}
          <div className="mb-4 rounded-lg border border-teal-100 bg-teal-50 p-4 dark:border-teal-900/40 dark:bg-teal-900/10">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-teal-600 dark:text-teal-400">
              Reflection Prompt
            </p>
            <p className="text-sm text-gray-700 dark:text-gray-300 italic">{day.reflection_prompt}</p>
          </div>

          {/* Verses */}
          {day.verses.length > 0 && (
            <div className="space-y-3">
              {day.verses.map((v) => (
                <VerseCard key={v.id} chunk={v} compact />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
