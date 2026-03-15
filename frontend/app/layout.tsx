import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Navbar from '@/components/Navbar';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'CrossVerse — Explore Religious Texts with AI',
  description:
    'AI-powered platform for exploring sacred scriptures across traditions. Ask questions, compare perspectives, and discover what every religion says about any topic.',
  keywords: [
    'religious texts', 'scripture', 'Bible', 'Quran', 'Bhagavad Gita',
    'Dhammapada', 'Guru Granth Sahib', 'AI', 'RAG', 'comparative religion',
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Navbar />
        <main className="min-h-screen">{children}</main>
      </body>
    </html>
  );
}
