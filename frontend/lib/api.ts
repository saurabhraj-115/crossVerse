import type {
  QueryRequest,
  QueryResponse,
  CompareRequest,
  CompareResponse,
  DebateRequest,
  DebateResponse,
  ContradictionRequest,
  ContradictionResponse,
  TopicsResponse,
  ScriptureChunk,
  SituationRequest,
  SituationResponse,
  FactCheckRequest,
  FactCheckResponse,
  EthicsRequest,
  EthicsResponse,
  DailyResponse,
  FingerprintQuestionsResponse,
  FingerprintAnalyzeRequest,
  FingerprintAnalyzeResponse,
  SimilarityVerseRequest,
  SimilarityVerseResponse,
  SimilarityGraphRequest,
  SimilarityGraphResponse,
  StudyRequest,
  StudyResponse,
  ArchaeologyRequest,
  ArchaeologyResponse,
  UniversalRequest,
  UniversalResponse,
  MoodRequest,
  MoodResponse,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchAPI<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const errorText = await response.text();
    let errorMessage: string;
    try {
      const errorJson = JSON.parse(errorText);
      errorMessage = errorJson.detail || errorJson.message || `HTTP ${response.status}`;
    } catch {
      errorMessage = errorText || `HTTP ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorMessage);
  }

  return response.json() as Promise<T>;
}

export async function queryScriptures(request: QueryRequest): Promise<QueryResponse> {
  return fetchAPI<QueryResponse>('/query', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function compareReligions(request: CompareRequest): Promise<CompareResponse> {
  return fetchAPI<CompareResponse>('/compare', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function debateReligions(request: DebateRequest): Promise<DebateResponse> {
  return fetchAPI<DebateResponse>('/debate', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function findContradictions(
  request: ContradictionRequest
): Promise<ContradictionResponse> {
  return fetchAPI<ContradictionResponse>('/contradictions', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getTopics(): Promise<TopicsResponse> {
  return fetchAPI<TopicsResponse>('/topics');
}

export async function getVerse(religion: string, ref: string): Promise<{ chunk: ScriptureChunk | null; message: string }> {
  const encodedRef = encodeURIComponent(ref);
  return fetchAPI(`/verse/${encodeURIComponent(religion)}/${encodedRef}`);
}

export async function getSituationWisdom(request: SituationRequest): Promise<SituationResponse> {
  return fetchAPI<SituationResponse>('/situations', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function factCheck(request: FactCheckRequest): Promise<FactCheckResponse> {
  return fetchAPI<FactCheckResponse>('/factcheck', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getEthicsPerspectives(request: EthicsRequest): Promise<EthicsResponse> {
  return fetchAPI<EthicsResponse>('/ethics', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getDailyBriefing(fresh = false): Promise<DailyResponse> {
  return fetchAPI<DailyResponse>(fresh ? '/daily?fresh=true' : '/daily');
}

export async function getFingerprintQuestions(): Promise<FingerprintQuestionsResponse> {
  return fetchAPI<FingerprintQuestionsResponse>('/fingerprint/questions');
}

export async function analyzeSpiritualFingerprint(
  request: FingerprintAnalyzeRequest
): Promise<FingerprintAnalyzeResponse> {
  return fetchAPI<FingerprintAnalyzeResponse>('/fingerprint/analyze', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function findSimilarVerses(request: SimilarityVerseRequest): Promise<SimilarityVerseResponse> {
  return fetchAPI<SimilarityVerseResponse>('/similarity/verse', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getSimilarityGraph(request: SimilarityGraphRequest): Promise<SimilarityGraphResponse> {
  return fetchAPI<SimilarityGraphResponse>('/similarity/graph', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function generateStudyPlan(request: StudyRequest): Promise<StudyResponse> {
  return fetchAPI<StudyResponse>('/study', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function archaeologyConcept(request: ArchaeologyRequest): Promise<ArchaeologyResponse> {
  return fetchAPI<ArchaeologyResponse>('/archaeology', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function findUniversalTruth(request: UniversalRequest): Promise<UniversalResponse> {
  return fetchAPI<UniversalResponse>('/universal', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getMoodScripture(request: MoodRequest): Promise<MoodResponse> {
  return fetchAPI<MoodResponse>('/mood', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}
