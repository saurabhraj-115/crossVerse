import type { Metadata } from 'next';
import DebateView from '@/components/DebateView';

export const metadata: Metadata = {
  title: 'Scripture Debate — CrossVerse',
  description: "Pose a question and watch each tradition's scriptures respond independently.",
};

export default function DebatePage() {
  return <DebateView />;
}
