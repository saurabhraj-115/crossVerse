export interface ScriptureChunk {
  id: string;
  religion: Religion;
  text: string;
  translation: string;
  book: string;
  chapter?: number | null;
  verse?: number | null;
  reference: string;
  source_url?: string | null;
  score?: number | null;
}

export type Religion =
  | 'Christianity'
  | 'Islam'
  | 'Hinduism'
  | 'Buddhism'
  | 'Judaism'
  | 'Sikhism';

export const ALL_RELIGIONS: Religion[] = [
  'Christianity',
  'Islam',
  'Hinduism',
  'Buddhism',
  'Judaism',
  'Sikhism',
];

export const RELIGION_COLORS: Record<Religion, string> = {
  Christianity: '#3B82F6',
  Islam: '#10B981',
  Hinduism: '#F59E0B',
  Buddhism: '#EAB308',
  Judaism: '#8B5CF6',
  Sikhism: '#14B8A6',
};

export const RELIGION_BG: Record<Religion, string> = {
  Christianity: 'bg-blue-100 text-blue-800 border-blue-200',
  Islam: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  Hinduism: 'bg-amber-100 text-amber-800 border-amber-200',
  Buddhism: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  Judaism: 'bg-purple-100 text-purple-800 border-purple-200',
  Sikhism: 'bg-teal-100 text-teal-800 border-teal-200',
};

export const RELIGION_EMOJI: Record<Religion, string> = {
  Christianity: '✝️',
  Islam: '☪️',
  Hinduism: '🕉️',
  Buddhism: '☸️',
  Judaism: '✡️',
  Sikhism: '🪯',
};

export type QueryMode = 'simple' | 'scholar';

export interface QueryRequest {
  question: string;
  religions?: Religion[] | null;
  mode: QueryMode;
}

export interface QueryResponse {
  answer: string;
  sources: ScriptureChunk[];
  question: string;
}

export interface CompareRequest {
  topic: string;
  religions: Religion[];
}

export interface CompareResponse {
  topic: string;
  perspectives: Record<Religion, ScriptureChunk[]>;
}

export interface DebateRequest {
  question: string;
  religions: Religion[];
}

export interface DebateResponse {
  question: string;
  responses: Record<Religion, QueryResponse>;
}

export interface ContradictionRequest {
  religion: Religion;
  topic: string;
}

export interface ContradictionPair {
  verse_a: ScriptureChunk | { reference: string };
  verse_b: ScriptureChunk | { reference: string };
  explanation: string;
}

export interface ContradictionResponse {
  religion: Religion;
  topic: string;
  contradictions: ContradictionPair[];
}

export interface TopicCategory {
  name: string;
  topics: string[];
}

export interface TopicsResponse {
  categories: TopicCategory[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: ScriptureChunk[];
  timestamp: Date;
}
