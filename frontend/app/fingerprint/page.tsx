'use client';

import { useEffect, useState } from 'react';
import { getFingerprintQuestions, analyzeSpiritualFingerprint } from '@/lib/api';
import {
  type FingerprintQuestion,
  type FingerprintAnswer,
  type FingerprintAnalyzeResponse,
  type Religion,
  RELIGION_COLORS,
  RELIGION_EMOJI,
  ALL_RELIGIONS,
} from '@/lib/types';
import VerseCard from '@/components/ui/VerseCard';
import { Fingerprint, Loader2, RotateCcw, ChevronRight } from 'lucide-react';
import clsx from 'clsx';

type Phase = 'loading' | 'quiz' | 'analyzing' | 'result' | 'error';

export default function FingerprintPage() {
  const [phase, setPhase] = useState<Phase>('loading');
  const [questions, setQuestions] = useState<FingerprintQuestion[]>([]);
  const [currentQ, setCurrentQ] = useState(0);
  const [answers, setAnswers] = useState<FingerprintAnswer[]>([]);
  const [result, setResult] = useState<FingerprintAnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadQuestions = async () => {
    setPhase('loading');
    setCurrentQ(0);
    setAnswers([]);
    setResult(null);
    setError(null);
    try {
      const data = await getFingerprintQuestions();
      setQuestions(data.questions);
      setPhase('quiz');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load questions.');
      setPhase('error');
    }
  };

  useEffect(() => {
    loadQuestions();
  }, []);

  const handleAnswer = async (option: string) => {
    const q = questions[currentQ];
    const newAnswers = [...answers, { question_id: q.id, answer: option }];
    setAnswers(newAnswers);

    if (currentQ < questions.length - 1) {
      setCurrentQ((i) => i + 1);
    } else {
      // Last question — analyze
      setPhase('analyzing');
      try {
        const data = await analyzeSpiritualFingerprint({ answers: newAnswers });
        setResult(data);
        setPhase('result');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Analysis failed. Please try again.');
        setPhase('error');
      }
    }
  };

  const progress = questions.length > 0 ? ((currentQ) / questions.length) * 100 : 0;

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-full bg-violet-100 text-violet-600 dark:bg-violet-900/40 dark:text-violet-400">
          <Fingerprint size={24} />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Spiritual Fingerprint</h1>
        <p className="mt-2 text-gray-500 dark:text-gray-400">
          10 questions to discover which tradition&apos;s worldview most aligns with yours.
        </p>
      </div>

      {/* Loading questions */}
      {phase === 'loading' && (
        <div className="flex items-center justify-center py-20 gap-3 text-gray-500 dark:text-gray-400">
          <Loader2 size={24} className="animate-spin" />
          Loading questions…
        </div>
      )}

      {/* Error */}
      {phase === 'error' && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center dark:border-red-900 dark:bg-red-900/20">
          <p className="mb-4 text-red-700 dark:text-red-400">{error}</p>
          <button
            onClick={loadQuestions}
            className="flex items-center gap-2 mx-auto rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
          >
            <RotateCcw size={14} /> Retry
          </button>
        </div>
      )}

      {/* Quiz */}
      {phase === 'quiz' && questions.length > 0 && (
        <div>
          {/* Progress bar */}
          <div className="mb-6">
            <div className="mb-1 flex justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>Question {currentQ + 1} of {questions.length}</span>
              <span>{Math.round(progress)}% complete</span>
            </div>
            <div className="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700">
              <div
                className="h-2 rounded-full bg-violet-600 transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Question card */}
          <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900">
            <h2 className="mb-6 text-lg font-bold text-gray-900 dark:text-gray-100">
              {questions[currentQ].question}
            </h2>
            <div className="space-y-3">
              {questions[currentQ].options.map((option, i) => (
                <button
                  key={i}
                  onClick={() => handleAnswer(option)}
                  className="group flex w-full items-center gap-3 rounded-xl border border-gray-200 p-4 text-left text-sm text-gray-700 hover:border-violet-400 hover:bg-violet-50 transition-all dark:border-gray-700 dark:text-gray-300 dark:hover:border-violet-600 dark:hover:bg-violet-900/20"
                >
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 border-gray-300 text-xs font-bold text-gray-400 group-hover:border-violet-500 group-hover:text-violet-600 transition-colors dark:border-gray-600 dark:group-hover:border-violet-400 dark:group-hover:text-violet-400">
                    {String.fromCharCode(65 + i)}
                  </span>
                  {option}
                  <ChevronRight size={14} className="ml-auto text-gray-300 group-hover:text-violet-500 transition-colors dark:text-gray-600 dark:group-hover:text-violet-400" />
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Analyzing */}
      {phase === 'analyzing' && (
        <div className="flex flex-col items-center justify-center py-20 gap-4 text-gray-500 dark:text-gray-400">
          <Loader2 size={32} className="animate-spin text-violet-600" />
          <p className="font-medium">Analyzing your worldview…</p>
          <p className="text-sm">Comparing against 6 traditions</p>
        </div>
      )}

      {/* Result */}
      {phase === 'result' && result && (
        <div className="space-y-6">
          {/* Primary match */}
          <div className="rounded-2xl bg-gradient-to-br from-violet-900 to-indigo-900 p-8 text-center text-white">
            <p className="mb-2 text-sm font-semibold uppercase tracking-widest text-violet-300">
              Your primary tradition
            </p>
            <div className="mb-2 text-5xl">
              {RELIGION_EMOJI[result.primary_tradition as Religion]}
            </div>
            <h2 className="text-3xl font-extrabold">{result.primary_tradition}</h2>
          </div>

          {/* Score bars */}
          <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900">
            <h3 className="mb-4 font-bold text-gray-800 dark:text-gray-200">Alignment Scores</h3>
            <div className="space-y-3">
              {ALL_RELIGIONS.sort((a, b) => (result.scores[b] ?? 0) - (result.scores[a] ?? 0)).map((r) => {
                const score = result.scores[r] ?? 0;
                const color = RELIGION_COLORS[r];
                return (
                  <div key={r}>
                    <div className="mb-1 flex items-center justify-between text-sm">
                      <span className="font-medium text-gray-700 dark:text-gray-300">
                        {RELIGION_EMOJI[r]} {r}
                      </span>
                      <span className="font-bold text-gray-600 dark:text-gray-400">
                        {Math.round(score * 100)}%
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-gray-100 dark:bg-gray-700">
                      <div
                        className="h-2 rounded-full transition-all duration-700"
                        style={{ width: `${score * 100}%`, backgroundColor: color }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Explanation */}
          <div className="rounded-2xl border border-violet-100 bg-violet-50 p-6 dark:border-violet-900/40 dark:bg-violet-900/10">
            <h3 className="mb-3 font-bold text-violet-800 dark:text-violet-300">What this means</h3>
            <p className="text-sm leading-relaxed text-gray-700 dark:text-gray-300">{result.explanation}</p>
          </div>

          {/* Key verses */}
          {result.key_verses.length > 0 && (
            <div>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Key passages from your tradition
              </h3>
              <div className="space-y-3">
                {result.key_verses.map((v) => (
                  <VerseCard key={v.id} chunk={v} />
                ))}
              </div>
            </div>
          )}

          {/* Retake */}
          <button
            onClick={loadQuestions}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-gray-200 py-3 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors dark:border-gray-700 dark:text-gray-400 dark:hover:bg-gray-800"
          >
            <RotateCcw size={15} /> Retake Quiz
          </button>
        </div>
      )}
    </div>
  );
}
