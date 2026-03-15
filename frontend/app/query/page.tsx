import type { Metadata } from 'next';
import QueryChat from '@/components/QueryChat';

export const metadata: Metadata = {
  title: 'Ask the Scriptures — CrossVerse',
  description: 'Ask any question and receive answers grounded exclusively in sacred scripture with citations.',
};

export default function QueryPage() {
  return (
    <div className="flex h-[calc(100vh-57px)] flex-col">
      <QueryChat />
    </div>
  );
}
