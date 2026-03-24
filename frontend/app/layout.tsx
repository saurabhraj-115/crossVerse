import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { ThemeProvider } from 'next-themes';
import { GoogleAnalytics } from '@next/third-parties/google';
import './globals.css';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import { SettingsProvider } from '@/lib/settings-context';
import PostHogProvider from '@/components/PostHogProvider';

const inter = Inter({ subsets: ['latin'] });

const APP_URL = 'https://crossverse.fly.dev';
const DESCRIPTION = 'Ask any question and get answers from 12 sacred traditions — Bible, Quran, Bhagavad Gita, and more. Always cited, never opinionated.';

export const metadata: Metadata = {
  title: 'CrossVerse — Explore Religious Texts with AI',
  description: DESCRIPTION,
  keywords: [
    'religious texts', 'scripture', 'Bible', 'Quran', 'Bhagavad Gita',
    'Dhammapada', 'Guru Granth Sahib', 'AI', 'RAG', 'comparative religion',
  ],
  metadataBase: new URL(APP_URL),
  openGraph: {
    type: 'website',
    url: APP_URL,
    siteName: 'CrossVerse',
    title: 'CrossVerse — Ask Any Question Across 12 Sacred Traditions',
    description: DESCRIPTION,
    images: [{ url: '/opengraph-image', width: 1200, height: 630, alt: 'CrossVerse' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'CrossVerse — Ask Any Question Across 12 Sacred Traditions',
    description: DESCRIPTION,
    images: ['/opengraph-image'],
  },
  icons: {
    icon: '/favicon.svg',
    shortcut: '/favicon.svg',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const gaId = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID;

  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <PostHogProvider>
          <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
            <SettingsProvider>
              <Navbar />
              <main className="min-h-screen">{children}</main>
              <Footer />
            </SettingsProvider>
          </ThemeProvider>
        </PostHogProvider>
        {gaId && <GoogleAnalytics gaId={gaId} />}
      </body>
    </html>
  );
}
