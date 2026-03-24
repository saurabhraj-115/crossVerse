import Link from 'next/link';
import { Github, Linkedin } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="border-t border-gray-200 bg-white px-4 py-8 dark:border-gray-800 dark:bg-gray-950">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 text-center sm:flex-row sm:justify-between sm:text-left">
        {/* Ownership */}
        <div>
          <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">
            CrossVerse &copy; {new Date().getFullYear()} Saurabh Raj
          </p>
          <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
            Free to use for personal &amp; educational purposes.{' '}
            <span className="font-medium text-amber-600 dark:text-amber-400">
              Commercial use is not permitted.
            </span>
          </p>
        </div>

        {/* Links */}
        <div className="flex items-center gap-4">
          <Link
            href="https://github.com/saurabhraj-115"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 transition-colors"
          >
            <Github size={14} />
            GitHub
          </Link>
          <Link
            href="https://www.linkedin.com/in/saurabhraj-ac/"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400 transition-colors"
          >
            <Linkedin size={14} />
            LinkedIn
          </Link>
        </div>
      </div>
    </footer>
  );
}
