'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTheme } from 'next-themes';
import { useEffect, useRef, useState } from 'react';
import clsx from 'clsx';
import {
  BookOpen, Scale, Swords, Compass, Sparkles, Sun, Moon, ChevronDown,
  Network, Microscope, Calendar, Heart, CheckCircle2, Flame,
  Fingerprint, GraduationCap, Settings,
} from 'lucide-react';
import SettingsPanel from '@/components/SettingsPanel';

const CORE_NAV = [
  { href: '/query', label: 'Ask', icon: BookOpen },
  { href: '/compare', label: 'Compare', icon: Scale },
  { href: '/debate', label: 'Debate', icon: Swords },
];

const EXPLORE_ITEMS = [
  { href: '/explore', label: 'Topic Explorer', icon: Compass, desc: 'Browse curated topics by theme' },
  { href: '/graph', label: 'Similarity Graph', icon: Network, desc: 'Visualize verse connections' },
  { href: '/archaeology', label: 'Archaeology', icon: Microscope, desc: 'Trace concepts across traditions' },
  { href: '/daily', label: 'Daily Briefing', icon: Calendar, desc: "Today's theme from all traditions" },
  { href: '/universal', label: 'Universal Truth', icon: Sparkles, desc: 'What all traditions agree on' },
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
        <div className="absolute right-0 top-10 z-50 w-[min(240px,calc(100vw-16px))] rounded-xl border border-gray-200 bg-white py-2 shadow-xl dark:border-gray-700 dark:bg-gray-900">
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
    <>
    <nav className="sticky top-0 z-50 border-b border-gray-200 bg-white/80 backdrop-blur-md dark:border-gray-800 dark:bg-gray-950/80">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="relative flex h-9 w-9 shrink-0 items-center justify-center">
            <svg viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg" className="h-9 w-9 drop-shadow-sm group-hover:drop-shadow-md transition-all">
              <defs>
                <linearGradient id="cvGrad" x1="0" y1="0" x2="36" y2="36" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#7C3AED"/>
                  <stop offset="100%" stopColor="#4F46E5"/>
                </linearGradient>
              </defs>
              {/* Outer circle */}
              <circle cx="18" cy="18" r="17" fill="url(#cvGrad)"/>
              {/* Six-fold radial lines — one per tradition */}
              <line x1="18" y1="4"  x2="18" y2="32" stroke="white" strokeWidth="1.2" strokeOpacity="0.25"/>
              <line x1="4"  y1="11" x2="32" y2="25" stroke="white" strokeWidth="1.2" strokeOpacity="0.25"/>
              <line x1="4"  y1="25" x2="32" y2="11" stroke="white" strokeWidth="1.2" strokeOpacity="0.25"/>
              {/* Inner hex ring */}
              <polygon points="18,8 24.2,11.5 24.2,18.5 18,22 11.8,18.5 11.8,11.5" fill="none" stroke="white" strokeWidth="1.3" strokeOpacity="0.5"/>
              {/* Centre dot */}
              <circle cx="18" cy="15" r="3.2" fill="white" fillOpacity="0.95"/>
            </svg>
          </div>
          <span className="font-extrabold text-gray-900 text-lg tracking-tight dark:text-white">
            Cross<span className="bg-gradient-to-r from-violet-600 to-indigo-500 bg-clip-text text-transparent">Verse</span>
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
              className="ml-1 flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100 transition-colors"
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            </button>
          )}

          {/* Settings */}
          <button
            onClick={() => setSettingsOpen(true)}
            title="Preferences (⌘,)"
            className="flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100 transition-colors"
            aria-label="Open settings"
          >
            <Settings size={16} />
          </button>
        </div>
      </div>

    </nav>
    <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </>
  );
}
