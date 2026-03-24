import type { Metadata } from 'next';
import QueryChat from '@/components/QueryChat';
import { ALL_RELIGIONS, type Religion } from '@/lib/types';

export const metadata: Metadata = {
  title: 'Ask the Scriptures — CrossVerse',
  description: 'Ask any question and receive answers grounded exclusively in sacred scripture with citations.',
};

export default function QueryPage({
  searchParams,
}: {
  searchParams: { q?: string; religions?: string };
}) {
  const initialQuestion = searchParams.q ? decodeURIComponent(searchParams.q) : undefined;
  const initialReligions: Religion[] | undefined = searchParams.religions
    ? decodeURIComponent(searchParams.religions)
        .split(',')
        .map((r) => r.trim() as Religion)
        .filter((r) => ALL_RELIGIONS.includes(r))
    : undefined;
  return (
    <div className="flex h-[calc(100vh-57px)] flex-col">
      <QueryChat initialQuestion={initialQuestion} initialReligions={initialReligions} />
    </div>
  );
}
