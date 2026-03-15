import type { Metadata } from 'next';
import CompareView from '@/components/CompareView';

export const metadata: Metadata = {
  title: 'Compare Traditions — CrossVerse',
  description: 'See what multiple religious traditions say about the same topic, side by side.',
};

export default function ComparePage() {
  return <CompareView />;
}
