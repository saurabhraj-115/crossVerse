'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { getSimilarityGraph } from '@/lib/api';
import {
  type SimilarityGraphResponse,
  type GraphNode,
  type Religion,
  RELIGION_COLORS,
  RELIGION_EMOJI,
  ALL_RELIGIONS,
} from '@/lib/types';
import { useSettings } from '@/lib/settings-context';
import { Network, Loader2, Search, X } from 'lucide-react';
import clsx from 'clsx';

// Dynamically import the graph canvas to avoid SSR issues
const GraphCanvas = dynamic(() => import('@/components/ui/GraphCanvas'), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center">
      <Loader2 size={24} className="animate-spin text-gray-400" />
    </div>
  ),
});

const CONCEPTS = [
  'love', 'forgiveness', 'prayer', 'suffering', 'soul', 'charity', 'justice',
];

export default function GraphPage() {
  const { globalReligions } = useSettings();
  const [concept, setConcept] = useState('');
  const [selectedReligions, setSelectedReligions] = useState<Religion[]>(globalReligions);
  const [graphData, setGraphData] = useState<SimilarityGraphResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  const toggleReligion = (r: Religion) => {
    setSelectedReligions((prev) =>
      prev.includes(r) ? prev.filter((x) => x !== r) : [...prev, r]
    );
  };

  const handleSearch = async (c: string = concept) => {
    if (!c.trim()) return;
    setLoading(true);
    setError(null);
    setSelectedNode(null);
    try {
      const data = await getSimilarityGraph({
        concept: c.trim(),
        religions: selectedReligions.length > 0 ? selectedReligions : null,
      });
      setGraphData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Graph generation failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-60px)] flex-col">
      {/* Controls bar */}
      <div className="border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-800 dark:bg-gray-950">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <Network size={18} className="text-indigo-600 dark:text-indigo-400" />
            <span className="font-bold text-gray-900 dark:text-gray-100 text-sm">Similarity Graph</span>
          </div>

          {/* Concept input */}
          <div className="flex flex-1 min-w-48 gap-2">
            <input
              type="text"
              value={concept}
              onChange={(e) => setConcept(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Enter a concept (e.g. love)…"
              className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500"
            />
            <button
              onClick={() => handleSearch()}
              disabled={!concept.trim() || loading}
              className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-40 transition-colors"
            >
              {loading ? <Loader2 size={13} className="animate-spin" /> : <Search size={13} />}
              {loading ? 'Building…' : 'Build'}
            </button>
          </div>

          {/* Quick concepts */}
          <div className="flex flex-wrap gap-1">
            {CONCEPTS.map((c) => (
              <button
                key={c}
                onClick={() => { setConcept(c); handleSearch(c); }}
                className="rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs text-gray-600 hover:border-indigo-300 hover:text-indigo-600 transition-colors dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:border-indigo-600 dark:hover:text-indigo-400"
              >
                {c}
              </button>
            ))}
          </div>

          {/* Religion filter */}
          <div className="flex flex-wrap gap-1">
            {ALL_RELIGIONS.map((r) => {
              const color = RELIGION_COLORS[r];
              const selected = selectedReligions.includes(r);
              return (
                <button
                  key={r}
                  onClick={() => toggleReligion(r)}
                  title={`${selected ? 'Hide' : 'Show'} ${r}`}
                  className={clsx(
                    'flex h-7 w-7 items-center justify-center rounded-full border text-sm transition-all',
                    selected ? 'border-current' : 'border-gray-200 dark:border-gray-700 opacity-40'
                  )}
                  style={selected ? { backgroundColor: color + '33', borderColor: color } : {}}
                >
                  {RELIGION_EMOJI[r]}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-auto mt-4 max-w-xl rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Graph area */}
      <div className="relative flex flex-1 overflow-hidden">
        {/* Empty state */}
        {!graphData && !loading && !error && (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 text-gray-400 dark:text-gray-600">
            <Network size={48} strokeWidth={1} />
            <p className="text-lg font-medium">Enter a concept to build the graph</p>
            <p className="text-sm">Verses become nodes · similarity &gt; 70% draws a connection</p>
            <p className="text-xs text-gray-400 dark:text-gray-600">Hover a node to see its connections light up</p>
          </div>
        )}

        {loading && (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 text-gray-500 dark:text-gray-400">
            <Loader2 size={32} className="animate-spin" />
            <p>Building similarity graph…</p>
          </div>
        )}

        {graphData && !loading && (
          <GraphCanvas
            data={graphData}
            onNodeClick={setSelectedNode}
            selectedNodeId={selectedNode?.id ?? null}
            selectedReligions={selectedReligions}
          />
        )}

        {/* Side panel */}
        {selectedNode && (
          <div className="absolute right-0 top-0 h-full w-80 overflow-y-auto border-l border-gray-200 bg-white p-4 shadow-xl dark:border-gray-700 dark:bg-gray-900">
            <div className="mb-3 flex items-center justify-between">
              <span className="font-bold text-gray-800 dark:text-gray-200 text-sm">Verse Detail</span>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <X size={16} />
              </button>
            </div>

            <div
              className="mb-3 rounded-lg p-3"
              style={{ backgroundColor: RELIGION_COLORS[selectedNode.religion as Religion] + '20' }}
            >
              <div className="mb-1 flex items-center gap-2">
                <span className="text-lg">{RELIGION_EMOJI[selectedNode.religion as Religion]}</span>
                <span className="font-bold text-gray-800 dark:text-gray-200 text-sm">{selectedNode.religion}</span>
              </div>
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">{selectedNode.reference}</p>
              <p className="text-sm leading-relaxed text-gray-700 dark:text-gray-300 italic">
                &ldquo;{selectedNode.text}&rdquo;
              </p>
            </div>

            <p className="text-xs text-gray-400 dark:text-gray-500">
              Relevance: {Math.round(selectedNode.score * 100)}%
            </p>

            {/* Legend */}
            <div className="mt-6">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">Legend</p>
              {ALL_RELIGIONS.map((r) => (
                <div key={r} className="mb-1 flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full" style={{ backgroundColor: RELIGION_COLORS[r] }} />
                  <span className="text-xs text-gray-600 dark:text-gray-400">{r}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
