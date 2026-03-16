'use client';

import { useEffect, useRef } from 'react';
import { X, Settings } from 'lucide-react';
import { ALL_RELIGIONS, RELIGION_COLORS, RELIGION_EMOJI, type Religion } from '@/lib/types';
import { useSettings } from '@/lib/settings-context';
import clsx from 'clsx';

interface SettingsPanelProps {
  open: boolean;
  onClose: () => void;
}

export default function SettingsPanel({ open, onClose }: SettingsPanelProps) {
  const { globalReligions, setGlobalReligions } = useSettings();
  const panelRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (open && panelRef.current && !panelRef.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open, onClose]);

  const toggle = (r: Religion) => {
    const next = globalReligions.includes(r)
      ? globalReligions.filter((x) => x !== r)
      : [...globalReligions, r];
    // Must have at least 1
    if (next.length > 0) setGlobalReligions(next);
  };

  const allSelected = globalReligions.length === ALL_RELIGIONS.length;

  return (
    <>
      {/* Backdrop */}
      <div
        className={clsx(
          'fixed inset-0 z-40 bg-black/30 backdrop-blur-sm transition-opacity duration-200',
          open ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        )}
        aria-hidden
      />

      {/* Panel */}
      <div
        ref={panelRef}
        className={clsx(
          'fixed right-0 top-0 z-50 flex h-full w-80 flex-col border-l border-gray-200 bg-white shadow-2xl transition-transform duration-300 dark:border-gray-800 dark:bg-gray-950',
          open ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4 dark:border-gray-800">
          <div className="flex items-center gap-2">
            <Settings size={16} className="text-indigo-500" />
            <span className="font-semibold text-gray-900 dark:text-gray-100">Preferences</span>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-800 dark:hover:text-gray-200 transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-6">

          {/* Religion filter */}
          <section>
            <div className="mb-1 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">
                Default Traditions
              </h3>
              <button
                onClick={() => setGlobalReligions(allSelected ? ['Christianity'] : [...ALL_RELIGIONS])}
                className="text-xs text-indigo-500 hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors"
              >
                {allSelected ? 'Clear all' : 'Select all'}
              </button>
            </div>
            <p className="mb-4 text-xs text-gray-400 dark:text-gray-500 leading-relaxed">
              These traditions are pre-selected on every page. You can still change them per page without affecting this setting.
            </p>

            <div className="space-y-2">
              {ALL_RELIGIONS.map((r) => {
                const active = globalReligions.includes(r);
                const color  = RELIGION_COLORS[r];
                return (
                  <button
                    key={r}
                    onClick={() => toggle(r)}
                    className={clsx(
                      'flex w-full items-center gap-3 rounded-xl border px-3.5 py-2.5 text-left text-sm font-medium transition-all',
                      active
                        ? 'border-transparent text-white shadow-sm'
                        : 'border-gray-200 bg-gray-50 text-gray-500 hover:border-gray-300 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-400 dark:hover:border-gray-600'
                    )}
                    style={active ? { backgroundColor: color, boxShadow: `0 2px 8px ${color}55` } : {}}
                  >
                    <span className="text-base">{RELIGION_EMOJI[r]}</span>
                    <span>{r}</span>
                    {!active && (
                      <span className="ml-auto text-[10px] font-normal text-gray-400 dark:text-gray-600">off</span>
                    )}
                  </button>
                );
              })}
            </div>

            {globalReligions.length < ALL_RELIGIONS.length && (
              <p className="mt-3 text-[11px] text-amber-500 dark:text-amber-400">
                {ALL_RELIGIONS.length - globalReligions.length} tradition{ALL_RELIGIONS.length - globalReligions.length > 1 ? 's' : ''} excluded from defaults
              </p>
            )}
          </section>

          {/* Divider */}
          <div className="border-t border-gray-100 dark:border-gray-800" />

          {/* Info */}
          <section>
            <h3 className="mb-1 text-sm font-semibold text-gray-800 dark:text-gray-200">About</h3>
            <p className="text-xs text-gray-400 dark:text-gray-500 leading-relaxed">
              CrossVerse searches sacred scriptures using AI embeddings. Results come only from the ingested texts — the AI does not generate or paraphrase scripture.
            </p>
          </section>
        </div>

        {/* Footer */}
        <div className="border-t border-gray-100 px-5 py-4 dark:border-gray-800">
          <p className="text-[11px] text-gray-400 dark:text-gray-600 text-center">
            Settings saved automatically · Ctrl+, to open
          </p>
        </div>
      </div>
    </>
  );
}
