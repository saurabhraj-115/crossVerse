'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTheme } from 'next-themes';
import { useEffect, useRef, useState } from 'react';
import clsx from 'clsx';
import {
  BookOpen, Scale, Swords, Compass, Sun, Moon, ChevronDown,
  Network, Microscope, Calendar, Heart, CheckCircle2, Flame,
  Fingerprint, GraduationCap, Settings,
} from 'lucide-react';
import SettingsPanel from '@/components/SettingsPanel';

const CORE_NAV = [
  { href: '/query', label: 'Ask', icon: BookOpen },
  { href: '/compare', label: 'Compare', icon: Scale },
  { href: '/debate', label: 'Debate', icon: Swords },
  { href: '/explore', label: 'Explore', icon: Compass },
];

const EXPLORE_ITEMS = [
  { href: '/graph', label: 'Similarity Graph', icon: Network, desc: 'Visualize verse connections' },
  { href: '/archaeology', label: 'Archaeology', icon: Microscope, desc: 'Trace concepts across traditions' },
  { href: '/daily', label: 'Daily Briefing', icon: Calendar, desc: "Today's theme from all traditions" },
];

const TOOLS_ITEMS = [
  { href: '/situations', label: 'Life Situations', icon: Heart, desc: 'Wisdom for hard moments' },
  { href: '/factcheck', label: 'Fact Check', icon: CheckCircle2, desc: 'Verify claims against scripture' },
  { href: '/ethics', label: 'Ethics', icon: Flame, desc: 'Dilemmas across traditions' },
  { href: '/fingerprint', label: 'Fingerprint', icon: Fingerprint, desc: 'Discover your tradition' },
  { href: '/study', label: 'Study Plans', icon: GraduationCap, desc: 'Multi-day curricula' },
];

interface DropdownProps {
  label: string;
  items: { href: string; label: string; icon: React.ElementType; desc: string }[];
  pathname: string;
}

function Dropdown({ label, items, pathname }: DropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const isActive = items.some((i) => i.href === pathname);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className={clsx(
          'flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
          isActive
            ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300'
            : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100'
        )}
      >
        {label}
        <ChevronDown
          size={13}
          className={clsx('transition-transform', open && 'rotate-180')}
        />
      </button>

      {open && (
        <div className="absolute right-0 top-10 z-50 w-60 rounded-xl border border-gray-200 bg-white py-2 shadow-xl dark:border-gray-700 dark:bg-gray-900">
          {items.map(({ href, label: itemLabel, icon: Icon, desc }) => (
            <Link
              key={href}
              href={href}
              onClick={() => setOpen(false)}
              className={clsx(
                'flex items-start gap-3 px-4 py-2.5 transition-colors',
                pathname === href
                  ? 'bg-indigo-50 dark:bg-indigo-900/30'
                  : 'hover:bg-gray-50 dark:hover:bg-gray-800'
              )}
            >
              <Icon
                size={16}
                className={clsx(
                  'mt-0.5 shrink-0',
                  pathname === href
                    ? 'text-indigo-600 dark:text-indigo-400'
                    : 'text-gray-400 dark:text-gray-500'
                )}
              />
              <div>
                <div
                  className={clsx(
                    'text-sm font-medium',
                    pathname === href
                      ? 'text-indigo-700 dark:text-indigo-300'
                      : 'text-gray-800 dark:text-gray-200'
                  )}
                >
                  {itemLabel}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">{desc}</div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Navbar() {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  useEffect(() => setMounted(true), []);

  // Ctrl+, opens settings
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === ',') {
        e.preventDefault();
        setSettingsOpen((v) => !v);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  return (
    <nav className="sticky top-0 z-50 border-b border-gray-200 bg-white/80 backdrop-blur-md dark:border-gray-800 dark:bg-gray-950/80">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 group">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-600 to-indigo-600 text-white text-sm font-bold shadow-sm group-hover:shadow-md transition-shadow">
            CV
          </div>
          <span className="font-bold text-gray-900 text-lg dark:text-white">
            Cross<span className="text-indigo-600 dark:text-indigo-400">Verse</span>
          </span>
        </Link>

        <div className="flex items-center gap-1">
          {/* Core nav links — hide labels on small screens */}
          {CORE_NAV.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={clsx(
                'flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors',
                pathname === href
                  ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100'
              )}
            >
              <Icon size={15} />
              <span className="hidden sm:inline">{label}</span>
            </Link>
          ))}

          {/* Explore dropdown */}
          <Dropdown label="Explore" items={EXPLORE_ITEMS} pathname={pathname} />

          {/* Tools dropdown */}
          <Dropdown label="Tools" items={TOOLS_ITEMS} pathname={pathname} />

          {/* Theme toggle */}
          {mounted && (
            <button
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="ml-1 flex h-8 w-8 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100 transition-colors"
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            </button>
          )}

          {/* Settings */}
          <button
            onClick={() => setSettingsOpen(true)}
            title="Preferences (⌘,)"
            className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100 transition-colors"
            aria-label="Open settings"
          >
            <Settings size={16} />
          </button>
        </div>
      </div>

      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </nav>
  );
}
