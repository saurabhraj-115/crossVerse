'use client';

import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { useTheme } from 'next-themes';
import type { SimilarityGraphResponse, GraphNode, Religion } from '@/lib/types';
import { RELIGION_COLORS, RELIGION_EMOJI } from '@/lib/types';

interface GraphCanvasProps {
  data: SimilarityGraphResponse;
  onNodeClick: (node: GraphNode) => void;
  selectedNodeId: string | null;
  selectedReligions: Religion[];
}

interface D3Node extends d3.SimulationNodeDatum {
  id: string;
  religion: string;
  reference: string;
  text: string;
  score: number;  // query-relevance (Qdrant score) — drives visual size/glow
  degree: number;
}

interface D3Link extends d3.SimulationLinkDatum<D3Node> {
  similarity: number;     // cross-religion cosine similarity, range > 0.7
  simNorm: number;        // (similarity - 0.7) / 0.3 → 0..1
  blendedColor: string;
}

interface Tooltip {
  x: number;
  y: number;
  node: D3Node;
  connectedCount: number;
}

// Abrahamic on right arc, Dharmic on left — creates a meaningful hemispheric split
const RELIGION_ANGLE: Record<string, number> = {
  Christianity: -90,
  Judaism:      -30,
  Islam:         30,
  Sikhism:       90,
  Buddhism:     150,
  Hinduism:     210,
};

function blendColors(c1: string, c2: string): string {
  const a = d3.color(c1)!.rgb();
  const b = d3.color(c2)!.rgb();
  return d3.rgb((a.r + b.r) / 2, (a.g + b.g) / 2, (a.b + b.b) / 2).formatHex();
}

function toRad(deg: number) { return (deg * Math.PI) / 180; }

export default function GraphCanvas({
  data,
  onNodeClick,
  selectedNodeId,
  selectedReligions,
}: GraphCanvasProps) {
  const svgRef      = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip]  = useState<Tooltip | null>(null);
  const [stats, setStats]      = useState({ nodes: 0, edges: 0, strong: 0 });
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme !== 'light';

  const scheduleHide = () => {
    hideTimerRef.current = setTimeout(() => setTooltip(null), 180);
  };
  const cancelHide = () => {
    if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
  };

  useEffect(() => {
    if (!svgRef.current) return;

    // Client-side religion filter
    const filteredNodes = data.nodes.filter((n) =>
      selectedReligions.includes(n.religion as Religion)
    );
    const filteredIds = new Set(filteredNodes.map((n) => n.id));
    const filteredEdges = data.edges.filter(
      (e) => filteredIds.has(e.source) && filteredIds.has(e.target)
    );

    // Snapshot religion per id before D3 mutates source/target
    const religionById = new Map(filteredNodes.map((n) => [n.id, n.religion]));

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    setTooltip(null);

    if (filteredNodes.length === 0) return;

    const width  = svgRef.current.clientWidth  || 900;
    const height = svgRef.current.clientHeight || 650;

    // Theme-aware palette
    const BG          = isDark ? '#080910' : '#f8fafc';
    const NODE_STROKE = isDark ? '#080910' : '#ffffff';
    const LABEL_FILL  = isDark ? '#4b5563' : '#94a3b8';
    const HULL_FILL_A = isDark ? '0d' : '18';      // hex alpha for hull fill
    const HULL_STK_O  = isDark ? 0.22 : 0.35;

    // Degree (# edges per node)
    const degreeMap = new Map<string, number>();
    filteredEdges.forEach((e) => {
      degreeMap.set(e.source, (degreeMap.get(e.source) ?? 0) + 1);
      degreeMap.set(e.target, (degreeMap.get(e.target) ?? 0) + 1);
    });

    const d3Nodes: D3Node[] = filteredNodes.map((n) => ({
      ...n,
      degree: degreeMap.get(n.id) ?? 0,
    }));

    // NOTE: backend skips same-religion pairs — ALL edges are cross-religion.
    const d3Links: D3Link[] = filteredEdges.map((e) => {
      const sr = religionById.get(e.source) ?? '';
      const tr = religionById.get(e.target) ?? '';
      const simNorm = Math.min(1, Math.max(0, (e.similarity - 0.7) / 0.3));
      return {
        source: e.source,
        target: e.target,
        similarity: e.similarity,
        simNorm,
        blendedColor: blendColors(
          RELIGION_COLORS[sr as Religion] ?? '#888',
          RELIGION_COLORS[tr as Religion] ?? '#888'
        ),
      };
    });

    const strongLinks = d3Links.filter((l) => l.simNorm > 0.75).length;
    setStats({ nodes: filteredNodes.length, edges: filteredEdges.length, strong: strongLinks });

    // Score stats — so we can normalize the ambient glow
    const scores  = d3Nodes.map((n) => n.score);
    const maxScore = Math.max(...scores, 0.001);
    const minScore = Math.min(...scores, 0);

    // Religion cluster centroids
    const clusterR = Math.min(width, height) * (selectedReligions.length <= 2 ? 0.14 : 0.27);
    const centroidMap = new Map<string, { x: number; y: number }>();
    selectedReligions.forEach((r, i) => {
      const angle = selectedReligions.length === 1
        ? 0
        : (RELIGION_ANGLE[r] ?? (i * (360 / selectedReligions.length)));
      centroidMap.set(r, {
        x: width  / 2 + clusterR * Math.cos(toRad(angle)),
        y: height / 2 + clusterR * Math.sin(toRad(angle)),
      });
    });
    if (selectedReligions.length === 1) {
      centroidMap.set(selectedReligions[0], { x: width / 2, y: height / 2 });
    }

    // Seed node positions near centroid
    d3Nodes.forEach((n) => {
      const c = centroidMap.get(n.religion);
      if (c) { n.x = c.x + (Math.random() - 0.5) * 80; n.y = c.y + (Math.random() - 0.5) * 80; }
    });

    // Node visual radius — SCORE is the primary driver (query relevance)
    // degree adds a small bonus for highly connected hubs
    const nodeRadius = (d: D3Node) => 7 + d.score * 18 + d.degree * 0.8;

    // ── SVG defs ─────────────────────────────────────────────────────────────

    const defs = svg.append('defs');

    // Hover glow
    const hoverGlowF = defs.append('filter').attr('id', 'hover-glow')
      .attr('x', '-60%').attr('y', '-60%').attr('width', '220%').attr('height', '220%');
    hoverGlowF.append('feGaussianBlur').attr('stdDeviation', '7').attr('result', 'blur');
    const hgm = hoverGlowF.append('feMerge');
    hgm.append('feMergeNode').attr('in', 'blur');
    hgm.append('feMergeNode').attr('in', 'SourceGraphic');

    // Ambient glow (always-on for high-score nodes)
    const ambientGlowF = defs.append('filter').attr('id', 'ambient-glow')
      .attr('x', '-80%').attr('y', '-80%').attr('width', '260%').attr('height', '260%');
    ambientGlowF.append('feGaussianBlur').attr('stdDeviation', '5').attr('result', 'blur');
    const agm = ambientGlowF.append('feMerge');
    agm.append('feMergeNode').attr('in', 'blur');
    agm.append('feMergeNode').attr('in', 'SourceGraphic');

    // Edge glow for strong bridges
    const edgeGlowF = defs.append('filter').attr('id', 'edge-glow')
      .attr('x', '-30%').attr('y', '-200%').attr('width', '160%').attr('height', '500%');
    edgeGlowF.append('feGaussianBlur').attr('stdDeviation', '2.5').attr('result', 'blur');
    const egm = edgeGlowF.append('feMerge');
    egm.append('feMergeNode').attr('in', 'blur');
    egm.append('feMergeNode').attr('in', 'SourceGraphic');

    // Radial gradient per node
    d3Nodes.forEach((n) => {
      const color = RELIGION_COLORS[n.religion as Religion] ?? '#6B7280';
      const id    = `ng-${n.id.replace(/[^a-zA-Z0-9]/g, '')}`;
      const g     = defs.append('radialGradient').attr('id', id);
      g.append('stop').attr('offset', '0%')
        .attr('stop-color', d3.color(color)?.brighter(1.2)?.toString() ?? color);
      g.append('stop').attr('offset', '100%').attr('stop-color', color);
    });

    // ── Zoom ─────────────────────────────────────────────────────────────────

    const g = svg.append('g');
    svg.call(
      d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 6])
        .on('zoom', (event) => { g.attr('transform', event.transform); setTooltip(null); })
    );

    // ── Layers ───────────────────────────────────────────────────────────────

    const hullLayer       = g.append('g').attr('class', 'hulls');
    const clusterLblLayer = g.append('g').attr('class', 'cluster-labels');
    const edgeLayer       = g.append('g').attr('class', 'edges');
    const edgeLabelLayer  = g.append('g').attr('class', 'edge-labels').attr('opacity', 0);
    const nodeLayer       = g.append('g').attr('class', 'nodes');

    // ── Convex hull blobs ─────────────────────────────────────────────────────

    const hullPaths = new Map<string, d3.Selection<SVGPathElement, unknown, null, undefined>>();
    const hullLine  = d3.line<[number, number]>().curve(d3.curveCatmullRomClosed.alpha(0.5));

    selectedReligions.forEach((r) => {
      const color = RELIGION_COLORS[r];
      hullPaths.set(r,
        hullLayer.append('path')
          .attr('fill', color + HULL_FILL_A)
          .attr('stroke', color)
          .attr('stroke-width', 1.5)
          .attr('stroke-opacity', HULL_STK_O)
          .attr('stroke-dasharray', '5 4')
          .attr('pointer-events', 'none')
          .attr('opacity', 0)
      );
    });

    // ── Cluster labels ────────────────────────────────────────────────────────

    type CE = [string, { x: number; y: number }];
    const clusterLabels = clusterLblLayer
      .selectAll<SVGTextElement, CE>('text')
      .data(Array.from(centroidMap.entries()) as CE[])
      .enter()
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('font-size', '11px')
      .attr('font-weight', '700')
      .attr('letter-spacing', '0.08em')
      .attr('fill', ([r]) => RELIGION_COLORS[r as Religion])
      .attr('opacity', 0.4)
      .attr('pointer-events', 'none')
      .text(([r]) => `${RELIGION_EMOJI[r as Religion]}  ${r.toUpperCase()}`);

    // ── Edges (ALL are cross-religion — backend enforces this) ────────────────

    const edge = edgeLayer
      .selectAll<SVGLineElement, D3Link>('line')
      .data(d3Links)
      .enter()
      .append('line')
      .attr('stroke', (d) => d.blendedColor)
      // Opacity: 0.15 at simNorm=0 → 0.85 at simNorm=1
      .attr('stroke-opacity', (d) => 0.15 + d.simNorm * 0.7)
      // Thickness: 0.8px at simNorm=0 → 7px at simNorm=1
      .attr('stroke-width',   (d) => 0.8 + d.simNorm * 6.2)
      .attr('stroke-linecap', 'round')
      // Only glow the strong connections
      .attr('filter', (d) => d.simNorm > 0.75 ? 'url(#edge-glow)' : null);

    // Similarity % labels on edges (shown when hovering a node)
    const edgeLabel = edgeLabelLayer
      .selectAll<SVGTextElement, D3Link>('text')
      .data(d3Links)
      .enter()
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('font-size', '9px')
      .attr('font-weight', '700')
      .attr('fill', (d) => d.blendedColor)
      .attr('pointer-events', 'none')
      .text((d) => `${Math.round(d.similarity * 100)}%`);

    // ── Nodes ─────────────────────────────────────────────────────────────────

    let simulation: d3.Simulation<D3Node, D3Link>;

    const node = nodeLayer
      .selectAll<SVGGElement, D3Node>('g')
      .data(d3Nodes)
      .enter()
      .append('g')
      .attr('cursor', 'pointer')
      .attr('opacity', 0)
      .call(
        d3.drag<SVGGElement, D3Node>()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x; d.fy = d.y;
          })
          .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
          .on('end',  (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null; d.fy = null;
          })
      );

    // Ambient glow ring — always-on, scales with query relevance (score)
    // High-score nodes literally glow on the canvas even before hover
    node.append('circle').attr('class', 'ambient-ring')
      .attr('r', (d) => nodeRadius(d) + 9)
      .attr('fill', (d) => RELIGION_COLORS[d.religion as Religion] + '00')
      .attr('stroke', (d) => RELIGION_COLORS[d.religion as Religion])
      .attr('stroke-width', (d) => 1 + d.score * 2.5)
      // opacity driven purely by normalized score — top nodes are clearly lit
      .attr('stroke-opacity', (d) => {
        const norm = (d.score - minScore) / (maxScore - minScore || 1);
        return norm * 0.55;
      })
      .attr('pointer-events', 'none');

    // Hover halo (hidden initially)
    node.append('circle').attr('class', 'halo')
      .attr('r', (d) => nodeRadius(d) + 12)
      .attr('fill', (d) => RELIGION_COLORS[d.religion as Religion] + '14')
      .attr('stroke', (d) => RELIGION_COLORS[d.religion as Religion])
      .attr('stroke-width', 1.5).attr('stroke-opacity', 0.5)
      .attr('opacity', 0);

    // Main circle
    node.append('circle').attr('class', 'main-dot')
      .attr('r', (d) => nodeRadius(d))
      .attr('fill', (d) => `url(#ng-${d.id.replace(/[^a-zA-Z0-9]/g, '')})`)
      .attr('stroke', NODE_STROKE).attr('stroke-width', 1.5);

    // Emoji
    node.append('text')
      .text((d) => RELIGION_EMOJI[d.religion as Religion] ?? '')
      .attr('text-anchor', 'middle').attr('dominant-baseline', 'central')
      .attr('font-size', (d) => Math.max(8, nodeRadius(d) * 0.82))
      .attr('pointer-events', 'none');

    // Score bar — tiny arc below node showing query relevance visually
    node.each(function (d) {
      const r = nodeRadius(d);
      const norm = (d.score - minScore) / (maxScore - minScore || 1);
      const color = RELIGION_COLORS[d.religion as Religion];
      // arc spans from -150° to -150° + norm*300°
      const startAngle = (-150 * Math.PI) / 180;
      const endAngle   = startAngle + norm * (300 * Math.PI) / 180;
      const arc = d3.arc<{ innerRadius: number; outerRadius: number; startAngle: number; endAngle: number }>()
        .innerRadius(r + 3)
        .outerRadius(r + 5)
        .startAngle(startAngle)
        .endAngle(endAngle)
        .cornerRadius(2);
      d3.select(this).append('path')
        .attr('d', arc({ innerRadius: r + 3, outerRadius: r + 5, startAngle, endAngle }))
        .attr('fill', color)
        .attr('opacity', 0.6)
        .attr('pointer-events', 'none');
    });

    // Reference label
    node.append('text').attr('class', 'ref-label')
      .text((d) => d.reference.length > 15 ? d.reference.slice(0, 15) + '…' : d.reference)
      .attr('x', 0).attr('y', (d) => nodeRadius(d) + 16)
      .attr('text-anchor', 'middle').attr('font-size', '8.5px')
      .attr('font-weight', '600').attr('letter-spacing', '0.02em')
      .attr('fill', LABEL_FILL).attr('pointer-events', 'none');

    // ── Hover ────────────────────────────────────────────────────────────────

    node
      .on('mouseenter', function (event, d) {
        cancelHide();

        const connectedIds   = new Set<string>();
        const connEdgeElems  = new Set<SVGLineElement>();
        const connLabelElems = new Set<SVGTextElement>();

        edge.each(function (l) {
          const s = (l.source as D3Node).id ?? (l.source as string);
          const t = (l.target as D3Node).id ?? (l.target as string);
          if (s === d.id || t === d.id) {
            connectedIds.add(s === d.id ? t : s);
            connEdgeElems.add(this as SVGLineElement);
          }
        });
        edgeLabel.each(function (l) {
          const s = (l.source as D3Node).id ?? (l.source as string);
          const t = (l.target as D3Node).id ?? (l.target as string);
          if (s === d.id || t === d.id) connLabelElems.add(this as SVGTextElement);
        });

        // Dim unrelated nodes sharply
        node.transition().duration(160)
          .attr('opacity', (nd) => nd.id === d.id || connectedIds.has(nd.id) ? 1 : 0.06);

        // Halo + enlarge
        d3.select(this).select('.halo').transition().duration(160).attr('opacity', 1);
        d3.select(this).select('.main-dot').transition().duration(160)
          .attr('r', nodeRadius(d) * 1.22)
          .attr('filter', 'url(#hover-glow)');

        // Connected edges: highlight, thicker, show similarity label
        edge.transition().duration(160)
          .attr('stroke-opacity', function (l) {
            return connEdgeElems.has(this as SVGLineElement) ? 0.97 : 0.03;
          })
          .attr('stroke-width', function (l) {
            return connEdgeElems.has(this as SVGLineElement) ? 2 + l.simNorm * 12 : 0.3;
          });

        // Show similarity % labels on connected edges
        edgeLabelLayer.transition().duration(160).attr('opacity', 1);
        edgeLabel
          .attr('opacity', function (l) {
            return connLabelElems.has(this as SVGTextElement) ? 1 : 0;
          });

        const rect = svgRef.current!.getBoundingClientRect();
        setTooltip({
          x: event.clientX - rect.left,
          y: event.clientY - rect.top,
          node: d,
          connectedCount: connectedIds.size,
        });
      })
      .on('mousemove', (event) => {
        if (!svgRef.current) return;
        const rect = svgRef.current.getBoundingClientRect();
        setTooltip((p) => p ? { ...p, x: event.clientX - rect.left, y: event.clientY - rect.top } : null);
      })
      .on('mouseleave', function (_, d) {
        node.transition().duration(240).attr('opacity', 1);
        d3.select(this).select('.halo').transition().duration(240).attr('opacity', 0);
        d3.select(this).select('.main-dot').transition().duration(240)
          .attr('r', nodeRadius(d)).attr('filter', null);

        edge.transition().duration(240)
          .attr('stroke-opacity', (l) => 0.15 + l.simNorm * 0.7)
          .attr('stroke-width',   (l) => 0.8 + l.simNorm * 6.2);

        edgeLabelLayer.transition().duration(200).attr('opacity', 0);
        scheduleHide();
      })
      .on('click', (_, d) => {
        const original = data.nodes.find((n) => n.id === d.id);
        if (original) onNodeClick(original as GraphNode);
      });

    // ── Force simulation ──────────────────────────────────────────────────────

    simulation = d3.forceSimulation<D3Node>(d3Nodes)
      .force(
        'link',
        d3.forceLink<D3Node, D3Link>(d3Links)
          .id((d) => d.id)
          .distance((d) => {
            // High similarity = short distance = pulled close on screen
            // Base distance long so clusters stay distinct; similarity shrinks it
            return 200 - d.simNorm * 150;
          })
          .strength((d) => 0.2 + d.simNorm * 0.4)
      )
      .force('charge', d3.forceManyBody().strength(-320))
      .force('center', d3.forceCenter(width / 2, height / 2).strength(0.03))
      .force('collision', d3.forceCollide<D3Node>((d) => nodeRadius(d) + 12))
      // Clustering force — keeps same-religion nodes near their centroid
      .force('cluster', (alpha: number) => {
        for (const d of d3Nodes) {
          const c = centroidMap.get(d.religion);
          if (!c) continue;
          d.vx = (d.vx ?? 0) - ((d.x ?? 0) - c.x) * 0.05 * alpha;
          d.vy = (d.vy ?? 0) - ((d.y ?? 0) - c.y) * 0.05 * alpha;
        }
      });

    // ── Hull updater ─────────────────────────────────────────────────────────

    function updateHulls() {
      selectedReligions.forEach((r) => {
        const rNodes = d3Nodes.filter((n) => n.religion === r && n.x != null && n.y != null);
        const path   = hullPaths.get(r);
        if (!path) return;
        if (rNodes.length < 3) { path.attr('d', null).attr('opacity', 0); return; }

        const pts  = rNodes.map((n) => [n.x!, n.y!] as [number, number]);
        const hull = d3.polygonHull(pts);
        if (!hull) { path.attr('d', null).attr('opacity', 0); return; }

        const cx = d3.mean(hull, (p) => p[0])!;
        const cy = d3.mean(hull, (p) => p[1])!;
        const inflated = hull.map(([x, y]): [number, number] => {
          const dx = x - cx, dy = y - cy;
          const len = Math.sqrt(dx * dx + dy * dy) || 1;
          return [x + (dx / len) * 40, y + (dy / len) * 40];
        });

        path.attr('d', hullLine(inflated)).attr('opacity', 1);
      });
    }

    function updateClusterLabels() {
      clusterLabels.attr('transform', ([r]: CE) => {
        const rNodes = d3Nodes.filter((n) => n.religion === r && n.x != null);
        if (rNodes.length === 0) {
          const c = centroidMap.get(r);
          return c ? `translate(${c.x},${c.y})` : '';
        }
        const cx   = d3.mean(rNodes, (n) => n.x!)!;
        const topY = d3.min(rNodes,  (n) => n.y!)! - 32;
        return `translate(${cx},${topY})`;
      });
    }

    // ── Tick ─────────────────────────────────────────────────────────────────

    simulation.on('tick', () => {
      updateHulls();
      updateClusterLabels();

      edge
        .attr('x1', (d) => (d.source as D3Node).x ?? 0)
        .attr('y1', (d) => (d.source as D3Node).y ?? 0)
        .attr('x2', (d) => (d.target as D3Node).x ?? 0)
        .attr('y2', (d) => (d.target as D3Node).y ?? 0);

      // Edge label: midpoint
      edgeLabel
        .attr('x', (d) => (((d.source as D3Node).x ?? 0) + ((d.target as D3Node).x ?? 0)) / 2)
        .attr('y', (d) => (((d.source as D3Node).y ?? 0) + ((d.target as D3Node).y ?? 0)) / 2 - 4);

      node.attr('transform', (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
    });

    // Staggered entry animation
    node.transition().duration(500).delay((_, i) => i * 28).attr('opacity', 1);

    return () => { simulation.stop(); };
  }, [data, selectedReligions, onNodeClick, isDark]);

  // Selected node ring
  useEffect(() => {
    if (!svgRef.current) return;
    const nodeStroke = isDark ? '#080910' : '#ffffff';
    d3.select(svgRef.current)
      .selectAll<SVGCircleElement, D3Node>('.main-dot')
      .attr('stroke', (d) => (d.id === selectedNodeId ? '#818cf8' : nodeStroke))
      .attr('stroke-width', (d) => (d.id === selectedNodeId ? 3.5 : 1.5));
  }, [selectedNodeId, isDark]);

  return (
    <div ref={containerRef} className="relative flex-1 h-full w-full">
      <svg
        ref={svgRef}
        className="h-full w-full"
        style={{ background: isDark ? '#080910' : '#f8fafc' }}
      />

      {/* Stats bar */}
      <div className="pointer-events-none absolute bottom-4 left-4 flex items-center gap-2 text-[11px] text-gray-600">
        <span>{stats.nodes} verses</span>
        <span>·</span>
        <span>{stats.edges} cross-faith links</span>
        {stats.strong > 0 && (
          <>
            <span>·</span>
            <span className="font-semibold" style={{ color: '#fbbf24' }}>
              {stats.strong} strong bridge{stats.strong !== 1 ? 's' : ''} ✦
            </span>
          </>
        )}
      </div>

      {/* Legend */}
      <div className="pointer-events-none absolute bottom-4 right-4 flex flex-col items-end gap-2 text-[11px] text-gray-600">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-0.5">
            <div className="h-0.5 w-3 rounded" style={{ background: '#4b5563' }} />
            <div className="h-0.5 w-5 rounded" style={{ background: '#6b7280' }} />
            <div className="h-1 w-6 rounded" style={{ background: '#9ca3af' }} />
          </div>
          <span>Edge = similarity (thicker → more similar)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1">
            <div className="h-3 w-3 rounded-full" style={{ background: '#374151', border: '1px solid #6b7280', opacity: 0.5 }} />
            <div className="h-4 w-4 rounded-full" style={{ background: '#4b5563', border: '1.5px solid #9ca3af' }} />
            <div className="h-5 w-5 rounded-full" style={{ background: '#6b7280', border: '2px solid #e5e7eb', boxShadow: '0 0 6px #e5e7eb55' }} />
          </div>
          <span>Node size + glow = query relevance</span>
        </div>
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="absolute z-50 w-72 rounded-2xl p-3.5 shadow-2xl"
          style={{
            left: tooltip.x + 18,
            top: Math.max(8, tooltip.y - 60),
            background: isDark ? 'rgba(10,10,20,0.97)' : 'rgba(255,255,255,0.97)',
            border: `1px solid ${RELIGION_COLORS[tooltip.node.religion as Religion]}40`,
            backdropFilter: 'blur(12px)',
            transform:
              svgRef.current && tooltip.x > svgRef.current.clientWidth * 0.65
                ? 'translateX(-108%)'
                : undefined,
          }}
          onMouseEnter={cancelHide}
          onMouseLeave={() => setTooltip(null)}
        >
          {/* Header */}
          <div className="mb-2 flex items-center gap-2">
            <span className="text-base">{RELIGION_EMOJI[tooltip.node.religion as Religion]}</span>
            <span className="text-xs font-bold" style={{ color: RELIGION_COLORS[tooltip.node.religion as Religion] }}>
              {tooltip.node.religion}
            </span>
            <span
              className="ml-auto rounded-full px-2 py-0.5 text-[10px] font-bold"
              style={{
                background: RELIGION_COLORS[tooltip.node.religion as Religion] + '22',
                color:      RELIGION_COLORS[tooltip.node.religion as Religion],
              }}
            >
              {Math.round(tooltip.node.score * 100)}% match
            </span>
          </div>

          {/* Score bar */}
          <div className="mb-2 flex items-center gap-2">
            <div className={`h-1.5 flex-1 rounded-full ${isDark ? 'bg-gray-800' : 'bg-gray-200'}`}>
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${Math.round(tooltip.node.score * 100)}%`,
                  background: RELIGION_COLORS[tooltip.node.religion as Religion],
                  boxShadow: `0 0 6px ${RELIGION_COLORS[tooltip.node.religion as Religion]}88`,
                }}
              />
            </div>
            <span className="text-[10px] text-gray-500">query relevance</span>
          </div>

          <p className="mb-1.5 text-[11px] font-semibold text-gray-400">{tooltip.node.reference}</p>
          <p className={`text-xs leading-relaxed italic line-clamp-3 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
            &ldquo;{tooltip.node.text}&rdquo;
          </p>

          {tooltip.connectedCount > 0 && (
            <p className="mt-2 text-[10px] text-gray-600">
              Connected to {tooltip.connectedCount} verse{tooltip.connectedCount !== 1 ? 's' : ''} from other traditions
            </p>
          )}

          <button
            className="mt-2.5 w-full rounded-lg py-1.5 text-[11px] font-semibold transition-colors"
            style={{
              background: RELIGION_COLORS[tooltip.node.religion as Religion] + '1e',
              color:      RELIGION_COLORS[tooltip.node.religion as Religion],
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background =
                RELIGION_COLORS[tooltip.node.religion as Religion] + '38';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background =
                RELIGION_COLORS[tooltip.node.religion as Religion] + '1e';
            }}
            onClick={() => onNodeClick(tooltip.node as unknown as GraphNode)}
          >
            Open full verse →
          </button>
        </div>
      )}
    </div>
  );
}
