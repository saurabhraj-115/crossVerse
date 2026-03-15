'use client';

import { useState, useRef, useEffect } from 'react';
import { queryScriptures } from '@/lib/api';
import {
  type ChatMessage,
  type HistoryMessage,
  type Religion,
  type QueryMode,
  ALL_RELIGIONS,
  RELIGION_EMOJI,
} from '@/lib/types';
import { useSettings } from '@/lib/settings-context';
import ChatMessageComponent from '@/components/ui/ChatMessage';
import { Send, Loader2, GraduationCap, MessageCircle, Mic, MicOff, Baby, Globe } from 'lucide-react';
import clsx from 'clsx';

const PROMPT_CATEGORIES = [
  {
    label: 'Life moments',
    color: 'text-rose-600 dark:text-rose-400',
    border: 'border-rose-200 dark:border-rose-800',
    bg: 'hover:bg-rose-50 dark:hover:bg-rose-900/20',
    prompts: [
      'I just lost someone I love',
      "I feel completely lost and don't know my purpose",
      'I failed at something I deeply cared about',
      'I feel alone even when surrounded by people',
    ],
  },
  {
    label: 'Inner struggles',
    color: 'text-amber-600 dark:text-amber-400',
    border: 'border-amber-200 dark:border-amber-800',
    bg: 'hover:bg-amber-50 dark:hover:bg-amber-900/20',
    prompts: [
      "I can't stop feeling angry at someone",
      'I carry guilt I cannot let go of',
      'I am overwhelmed by fear and anxiety',
      'I feel envious of others and ashamed of it',
    ],
  },
  {
    label: 'Big questions',
    color: 'text-indigo-600 dark:text-indigo-400',
    border: 'border-indigo-200 dark:border-indigo-800',
    bg: 'hover:bg-indigo-50 dark:hover:bg-indigo-900/20',
    prompts: [
      'Why do innocent people suffer?',
      'Is there meaning after death?',
      'How do I know what is right from wrong?',
      'Does prayer actually change anything?',
    ],
  },
  {
    label: 'Relationships',
    color: 'text-emerald-600 dark:text-emerald-400',
    border: 'border-emerald-200 dark:border-emerald-800',
    bg: 'hover:bg-emerald-50 dark:hover:bg-emerald-900/20',
    prompts: [
      'How do I forgive someone who hurt me deeply?',
      'What does scripture say about loving your enemy?',
      'How should I treat the poor and suffering?',
      'What makes a good and meaningful life?',
    ],
  },
];

// Auto-detect religion mentions in a question
const RELIGION_KEYWORDS: Record<string, Religion> = {
  christian: 'Christianity', christianity: 'Christianity', bible: 'Christianity',
  jesus: 'Christianity', christ: 'Christianity', gospel: 'Christianity',
  islam: 'Islam', muslim: 'Islam', quran: 'Islam', islamic: 'Islam',
  allah: 'Islam', muhammad: 'Islam', prophet: 'Islam',
  hindu: 'Hinduism', hinduism: 'Hinduism', gita: 'Hinduism',
  vedic: 'Hinduism', krishna: 'Hinduism', upanishad: 'Hinduism', vedanta: 'Hinduism',
  buddhism: 'Buddhism', buddhist: 'Buddhism', buddha: 'Buddhism',
  dhamma: 'Buddhism', dharma: 'Buddhism', pali: 'Buddhism',
  jewish: 'Judaism', judaism: 'Judaism', torah: 'Judaism',
  hebrew: 'Judaism', talmud: 'Judaism', rabbi: 'Judaism',
  sikh: 'Sikhism', sikhism: 'Sikhism', granth: 'Sikhism', guru: 'Sikhism',
};

function detectReligions(text: string): Religion[] {
  const lower = text.toLowerCase();
  const detected = new Set<Religion>();
  for (const [keyword, religion] of Object.entries(RELIGION_KEYWORDS)) {
    if (lower.includes(keyword)) detected.add(religion);
  }
  return Array.from(detected);
}

export default function QueryChat() {
  const { globalReligions } = useSettings();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<QueryMode>('simple');
  const [selectedReligions, setSelectedReligions] = useState<Religion[]>(globalReligions);
  const [language, setLanguage] = useState<string>('English');
  const [error, setError] = useState<string | null>(null);
  const [listening, setListening] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null);

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

    // Auto-detect religions if none are manually selected
    const autoDetected = selectedReligions.length === 0 ? detectReligions(text) : [];
    const religionsToUse =
      selectedReligions.length > 0 ? selectedReligions :
      autoDetected.length > 0 ? autoDetected : null;

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
      const history: HistoryMessage[] = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const response = await queryScriptures({
        question: text.trim(),
        religions: religionsToUse,
        mode,
        history: history.length > 0 ? history : null,
        language: language !== 'English' ? language : null,
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

  const toggleVoice = async () => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setError('Voice input is not supported in this browser. Try Chrome or Edge.');
      return;
    }

    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    // Request mic permission explicitly first — this surfaces the browser prompt
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((t) => t.stop()); // release immediately; recognition takes over
    } catch {
      setError('Microphone access denied. Please allow microphone access in your browser settings.');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = true;
    recognition.continuous = false;
    recognitionRef.current = recognition;

    recognition.onstart = () => {
      setListening(true);
      setError(null);
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = (event: any) => {
      setListening(false);
      if (event.error === 'not-allowed') {
        setError('Microphone access denied. Allow it in browser settings and try again.');
      } else if (event.error === 'no-speech') {
        setError('No speech detected. Try speaking louder or closer to the mic.');
      } else {
        setError(`Voice input error: ${event.error}`);
      }
    };

    recognition.onresult = (event: any) => {
      const transcript = Array.from(event.results as any[])
        .map((r: any) => r[0].transcript)
        .join('');
      setInput(transcript);
      if (event.results[event.results.length - 1].isFinal) {
        recognition.stop();
      }
    };

    recognition.start();
  };

  return (
    <div className="flex h-full flex-col">
      {/* Controls bar */}
      <div className="border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-800 dark:bg-gray-900">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-4">
          {/* Mode toggle — 3-way */}
          <div className="flex items-center gap-1 rounded-lg bg-gray-100 p-1 dark:bg-gray-800">
            {([
              { key: 'child', label: 'Child', Icon: Baby },
              { key: 'simple', label: 'Simple', Icon: MessageCircle },
              { key: 'scholar', label: 'Scholar', Icon: GraduationCap },
            ] as { key: QueryMode; label: string; Icon: React.ElementType }[]).map(({ key, label, Icon }) => (
              <button
                key={key}
                onClick={() => setMode(key)}
                className={clsx(
                  'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                  mode === key
                    ? 'bg-white text-gray-900 shadow-sm dark:bg-gray-700 dark:text-gray-100'
                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
                )}
              >
                <Icon size={13} />
                {label}
              </button>
            ))}
          </div>

          {/* Language selector */}
          <div className="flex items-center gap-1.5">
            <Globe size={13} className="text-gray-400" />
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="rounded-md border border-gray-200 bg-white py-1 pl-2 pr-6 text-xs text-gray-700 focus:border-indigo-400 focus:outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"
            >
              {['English','Spanish','French','German','Arabic','Hindi','Portuguese','Mandarin','Bengali','Urdu'].map((lang) => (
                <option key={lang} value={lang}>{lang}</option>
              ))}
            </select>
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
                    ? 'border-indigo-400 bg-indigo-50 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 dark:border-indigo-600'
                    : 'border-gray-200 bg-white text-gray-500 hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:border-gray-600'
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
            <div className="py-8">
              <div className="mb-8 text-center">
                <div className="mb-3 text-4xl">📖</div>
                <h2 className="mb-2 text-xl font-bold text-gray-800 dark:text-gray-200">
                  What's on your mind?
                </h2>
                <p className="mx-auto max-w-sm text-sm text-gray-500 dark:text-gray-400">
                  You don't need a religious question. Describe something real —
                  scripture from six traditions will speak to it.
                </p>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                {PROMPT_CATEGORIES.map((cat) => (
                  <div
                    key={cat.label}
                    className={`rounded-xl border bg-white p-4 dark:bg-gray-900 ${cat.border}`}
                  >
                    <p className={`mb-3 text-xs font-bold uppercase tracking-wider ${cat.color}`}>
                      {cat.label}
                    </p>
                    <div className="space-y-1">
                      {cat.prompts.map((p) => (
                        <button
                          key={p}
                          onClick={() => sendMessage(p)}
                          className={`w-full rounded-lg border border-transparent px-3 py-2 text-left text-sm text-gray-700 transition-colors dark:text-gray-300 ${cat.bg} hover:border-gray-200 dark:hover:border-gray-700`}
                        >
                          {p}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              <p className="mt-6 text-center text-xs text-gray-400 dark:text-gray-600">
                Every answer is grounded exclusively in scripture — no opinions, always cited.
              </p>
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
              <div className="rounded-2xl bg-gray-50 border border-gray-200 px-4 py-3 dark:bg-gray-800 dark:border-gray-700">
                <div className="flex gap-1">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.3s]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.15s]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400" />
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-900/20 dark:text-red-400">
              {error}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 bg-white px-4 py-4 dark:border-gray-800 dark:bg-gray-900">
        <form onSubmit={handleSubmit} className="mx-auto max-w-3xl">
          <div className="flex items-end gap-3 rounded-xl border border-gray-300 bg-white p-2 shadow-sm focus-within:border-indigo-400 focus-within:ring-1 focus-within:ring-indigo-400 transition-all dark:border-gray-700 dark:bg-gray-800 dark:focus-within:border-indigo-500 dark:focus-within:ring-indigo-500">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about scripture… (Enter to send, Shift+Enter for new line)"
              rows={1}
              className="flex-1 resize-none bg-transparent px-2 py-1 text-sm text-gray-900 placeholder-gray-400 outline-none dark:text-gray-100 dark:placeholder-gray-500"
              style={{ maxHeight: '120px' }}
              disabled={loading}
            />
            <button
              type="button"
              onClick={toggleVoice}
              disabled={loading}
              className={clsx(
                'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-colors disabled:cursor-not-allowed disabled:opacity-40',
                listening
                  ? 'bg-red-500 text-white animate-pulse'
                  : 'text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300'
              )}
              title={listening ? 'Stop recording' : 'Voice input'}
            >
              {listening ? <MicOff size={15} /> : <Mic size={15} />}
            </button>
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Send size={15} />
            </button>
          </div>
          <p className="mt-2 text-center text-xs text-gray-400 dark:text-gray-500">
            Answers are grounded exclusively in scripture. Always cite primary sources.
          </p>
        </form>
      </div>
    </div>
  );
}
