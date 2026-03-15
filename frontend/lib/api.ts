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
