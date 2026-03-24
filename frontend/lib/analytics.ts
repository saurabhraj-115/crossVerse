/**
 * Thin wrapper over PostHog so call sites don't import posthog-js directly.
 * Safe to call server-side (no-ops when window is undefined).
 */

type EventProperties = Record<string, string | number | boolean | null | undefined>;

function ph() {
  if (typeof window === 'undefined') return null;
  // posthog-js attaches itself to window after init
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (window as any).posthog ?? null;
}

export function track(event: string, props?: EventProperties) {
  ph()?.capture(event, props);
}

// ── Named events ─────────────────────────────────────────────────────────────

export const Analytics = {
  questionAsked(question: string, mode: string, religions: string[]) {
    track('question_asked', { question_length: question.length, mode, religion_count: religions.length, religions: religions.join(',') });
  },
  dailyCardOpened(religion: string, theme: string) {
    track('daily_card_opened', { religion, theme });
  },
  shareCardDownloaded(religion: string, theme: string) {
    track('share_card_downloaded', { religion, theme });
  },
  whatsappShareClicked(religion: string, theme: string) {
    track('whatsapp_share_clicked', { religion, theme });
  },
  dailyRefreshed() {
    track('daily_refreshed');
  },
  dailyThemeLoaded(theme: string, source: 'news' | 'fallback') {
    track('daily_theme_loaded', { theme, source });
  },
  moodSelected(mood: string) {
    track('mood_selected', { mood });
  },
  topicClicked(topic: string) {
    track('topic_clicked', { topic });
  },
  featureCardClicked(feature: string, href: string) {
    track('feature_card_clicked', { feature, href });
  },
  compareSubmitted(topic: string, religionCount: number) {
    track('compare_submitted', { topic_length: topic.length, religion_count: religionCount });
  },
  debateSubmitted(topic: string, religionCount: number) {
    track('debate_submitted', { topic_length: topic.length, religion_count: religionCount });
  },
  ethicsSubmitted(dilemma: string) {
    track('ethics_submitted', { dilemma_length: dilemma.length });
  },
  situationsSubmitted(situation: string) {
    track('situations_submitted', { situation_length: situation.length });
  },
  factcheckSubmitted(claim: string, religion: string) {
    track('factcheck_submitted', { claim_length: claim.length, religion });
  },
  fingerprintCompleted(topTradition: string) {
    track('fingerprint_completed', { top_tradition: topTradition });
  },
  archaeologySubmitted(concept: string) {
    track('archaeology_submitted', { concept });
  },
};
