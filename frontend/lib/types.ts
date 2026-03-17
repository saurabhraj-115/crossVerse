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
  | 'Sikhism'
  | 'Jainism'
  | 'Zoroastrianism'
  | 'Confucianism'
  | 'Taoism';

export const ALL_RELIGIONS: Religion[] = [
  'Christianity',
  'Islam',
  'Hinduism',
  'Buddhism',
  'Judaism',
  'Sikhism',
  'Jainism',
  'Zoroastrianism',
  'Confucianism',
  'Taoism',
];

export const RELIGION_COLORS: Record<Religion, string> = {
  Christianity: '#3B82F6',
  Islam: '#10B981',
  Hinduism: '#F59E0B',
  Buddhism: '#EAB308',
  Judaism: '#8B5CF6',
  Sikhism: '#14B8A6',
  Jainism: '#EA580C',
  Zoroastrianism: '#D97706',
  Confucianism: '#78716C',
  Taoism: '#059669',
};

export const RELIGION_BG: Record<Religion, string> = {
  Christianity: 'bg-blue-100 text-blue-800 border-blue-200',
  Islam: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  Hinduism: 'bg-amber-100 text-amber-800 border-amber-200',
  Buddhism: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  Judaism: 'bg-purple-100 text-purple-800 border-purple-200',
  Sikhism: 'bg-teal-100 text-teal-800 border-teal-200',
  Jainism: 'bg-orange-100 text-orange-800 border-orange-200',
  Zoroastrianism: 'bg-amber-100 text-amber-800 border-amber-300',
  Confucianism: 'bg-stone-100 text-stone-800 border-stone-200',
  Taoism: 'bg-emerald-100 text-emerald-900 border-emerald-300',
};

export const RELIGION_EMOJI: Record<Religion, string> = {
  Christianity: '✝️',
  Islam: '☪️',
  Hinduism: '🕉️',
  Buddhism: '☸️',
  Judaism: '✡️',
  Sikhism: '🪯',
  Jainism: '🌊',
  Zoroastrianism: '🔥',
  Confucianism: '📖',
  Taoism: '☯️',
};

export type QueryMode = 'simple' | 'scholar' | 'child';

export interface HistoryMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface QueryRequest {
  question: string;
  religions?: Religion[] | null;
  mode: QueryMode;
  history?: HistoryMessage[] | null;
  language?: string | null;
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

// ---------------------------------------------------------------------------
// Situations
// ---------------------------------------------------------------------------
export interface SituationRequest {
  situation: string;
  religions?: Religion[] | null;
}

export interface SituationResponse {
  wisdom: string;
  sources: ScriptureChunk[];
  situation: string;
}

// ---------------------------------------------------------------------------
// Fact-check
// ---------------------------------------------------------------------------
export interface FactCheckRequest {
  claim: string;
  religion: Religion;
}

export type FactCheckVerdict = 'supported' | 'contradicted' | 'not_found' | 'nuanced';

export interface FactCheckResponse {
  claim: string;
  religion: Religion;
  verdict: FactCheckVerdict;
  explanation: string;
  sources: ScriptureChunk[];
}

// ---------------------------------------------------------------------------
// Ethics
// ---------------------------------------------------------------------------
export interface EthicsRequest {
  dilemma: string;
  religions?: Religion[] | null;
}

export interface EthicsResponse {
  dilemma: string;
  perspectives: Record<Religion, string>;
  sources: Record<Religion, ScriptureChunk[]>;
}

// ---------------------------------------------------------------------------
// Daily
// ---------------------------------------------------------------------------
export interface DailyPerspective {
  reflection: string;
  sources: ScriptureChunk[];
}

export interface DailyResponse {
  theme: string;
  date: string;
  perspectives: Record<Religion, DailyPerspective>;
}

// ---------------------------------------------------------------------------
// Fingerprint
// ---------------------------------------------------------------------------
export interface FingerprintQuestion {
  id: number;
  question: string;
  options: string[];
}

export interface FingerprintQuestionsResponse {
  questions: FingerprintQuestion[];
}

export interface FingerprintAnswer {
  question_id: number;
  answer: string;
}

export interface FingerprintAnalyzeRequest {
  answers: FingerprintAnswer[];
}

export interface FingerprintAnalyzeResponse {
  primary_tradition: Religion;
  scores: Record<Religion, number>;
  explanation: string;
  key_verses: ScriptureChunk[];
}

// ---------------------------------------------------------------------------
// Similarity graph
// ---------------------------------------------------------------------------
export interface SimilarityVerseRequest {
  reference: string;
  religion: Religion;
  top_k?: number;
}

export interface SimilarityVerseResponse {
  reference: string;
  religion: Religion;
  similar_verses: ScriptureChunk[];
}

export interface GraphNode {
  id: string;
  religion: Religion;
  reference: string;
  text: string;
  score: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  similarity: number;
}

export interface SimilarityGraphRequest {
  concept: string;
  religions?: Religion[] | null;
}

export interface SimilarityGraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ---------------------------------------------------------------------------
// Study plan
// ---------------------------------------------------------------------------
export interface StudyRequest {
  topic: string;
  days?: number;
  religions?: Religion[] | null;
}

export interface StudyDay {
  day: number;
  theme: string;
  verses: ScriptureChunk[];
  reflection_prompt: string;
}

export interface StudyResponse {
  topic: string;
  days: StudyDay[];
}

// ---------------------------------------------------------------------------
// Archaeology
// ---------------------------------------------------------------------------
export interface ArchaeologyRequest {
  concept: string;
}

export interface ArchaeologyResponse {
  concept: string;
  analysis: string;
  sources: ScriptureChunk[];
}

// ---------------------------------------------------------------------------
// Universal Truth
// ---------------------------------------------------------------------------
export interface UniversalRequest {
  concept: string;
  religions?: Religion[] | null;
}

export interface TraditionExpression {
  verse_text: string;
  reference: string;
  reflection: string;
}

export interface UniversalResponse {
  concept: string;
  universal_truth: string;
  tradition_expressions: Record<Religion, TraditionExpression>;
  sources: ScriptureChunk[];
}

// ---------------------------------------------------------------------------
// Mood Scripture
// ---------------------------------------------------------------------------
export type MoodType =
  | 'grief' | 'joy' | 'anxiety' | 'fear' | 'hope'
  | 'loneliness' | 'anger' | 'gratitude' | 'confusion' | 'love';

export interface MoodRequest {
  mood: MoodType;
}

export interface MoodResponse {
  mood: string;
  message: string;
  verses: ScriptureChunk[];
  sources: ScriptureChunk[];
}
