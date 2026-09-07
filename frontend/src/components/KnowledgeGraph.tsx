import React, { useState, useRef, useEffect, useCallback } from 'react';
import { mockAdapter, useMock } from '../api/mockAdapter';

type KGNodeType =
  | 'policy' | 'agency' | 'instrument' | 'budget' | 'project' | 'risk'
  | 'contractor' | 'portfolio' | 'currency' | 'counterparty' | 'scenario'
  | 'strategy' | 'debt_issuance';

interface KGNode {
  id: string;
  label: string;
  type: KGNodeType;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  radius?: number;
  color: string;
  data?: Record<string, unknown>;
}

interface KGEdge {
  source: string;
  target: string;
  label: string;
  weight: number;
  type: 'issued_by' | 'funds_project' | 'part_of' | 'subject_to' | 'contracted_by' | 'regulates' | 'supports' | 'associated_with' | 'holds' | 'denominated' | 'affects' | 'uses';
}

interface KGData {
  nodes: KGNode[];
  edges: KGEdge[];
}

interface SearchResult {
  nodes: KGNode[];
  edges: KGEdge[];
  total: number;
}

const NODE_COLORS: Record<KGNodeType, string> = {
  policy: '#8b5cf6',
  agency: '#06b6d4',
  instrument: '#22d3ee',
  budget: '#a78bfa',
  project: '#f472b6',
  risk: '#f97316',
  contractor: '#10b981',
  portfolio: '#6366f1',
  currency: '#f59e0b',
  counterparty: '#84cc16',
  scenario: '#e879f9',
  strategy: '#38bdf8',
  debt_issuance: '#22d3ee' };

const NODE_ICONS: Record<KGNodeType, string> = {
  policy: 'Shield',
  agency: 'Building',
  instrument: 'TrendingUp',
  budget: 'DollarSign',
  project: 'HardHat',
  risk: 'Warning',
  contractor: 'User',
  portfolio: 'Folder',
  currency: 'DollarSign',
  counterparty: 'User',
  scenario: 'Activity',
  strategy: 'Target',
  debt_issuance: 'TrendingUp' };

const EDGE_COLORS: Record<KGEdge['type'], string> = {
  issued_by: '#06b6d4',
  funds_project: '#a78bfa',
  part_of: '#f472b6',
  subject_to: '#f97316',
  contracted_by: '#10b981',
  regulates: '#8b5cf6',
  supports: '#ec4899',
  associated_with: '#fbbf24',
  holds: '#6366f1',
  denominated: '#22d3ee',
  affects: '#f472b6',
  uses: '#10b981' };

interface SearchFilters {
  nodeTypes?: KGNodeType[];
  nameContains?: string;
}

export interface GraphViewProps {
  initialNodes?: KGNode[];
  initialEdges?: KGEdge[];
}

export interface SearchState {
  query: string;
  nodeTypes: KGNodeType[];
  loading: boolean;
  error: string | null;
  data?: SearchResult;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  total?: number;
}

// Mock API search function - in production this would call the backend
async function searchKnowledgeGraphApi(
  query: string,
  nodeTypes: KGNodeType[],
  filters?: SearchFilters
): Promise<ApiResponse<SearchResult>> {
  // Simulate API call
  await new Promise((resolve) => setTimeout(resolve, 500));

  // Mock data for demonstration
  const mockResults: Record<string, { nodes: KGNode[]; edges: KGEdge[] }> = {
    policy: {
      nodes: [
        { id: 'policy-1', label: 'Debt Ceiling Rule', type: 'policy', color: '#8b5cf6', data: { rule_type: 'debt_ceiling', threshold_value: 60 } },
        { id: 'policy-2', label: 'Fiscal Rule 2026', type: 'policy', color: '#8b5cf6', data: { rule_type: 'deficit_limit', threshold_value: 3 } },
      ],
      edges: [] },
    agency: {
      nodes: [
        { id: 'agency-1', label: 'Treasury Department', type: 'agency', color: '#06b6d4', data: { entity_type: 'national' } },
        { id: 'agency-2', label: 'Central Bank', type: 'agency', color: '#06b6d4', data: { entity_type: 'national' } },
      ],
      edges: [] },
    project: {
      nodes: [
        { id: 'project-1', label: 'Infrastructure Project Alpha', type: 'project', color: '#f472b6', data: {} },
        { id: 'project-2', label: 'Renewable Energy Initiative', type: 'project', color: '#f472b6', data: {} },
      ],
      edges: [] },
    debt_issuance: {
      nodes: [
        { id: 'debt-1', label: 'US Treasury 10Y', type: 'instrument', color: '#22d3ee', data: { instrument_type: 'treasury_bond' } },
        { id: 'debt-2', label: 'EUR Sovereign Bond', type: 'instrument', color: '#22d3ee', data: { instrument_type: 'sovereign_bond' } },
      ],
      edges: [] },
    budget: {
      nodes: [
        { id: 'budget-1', label: 'FY2026 Operating Budget', type: 'budget', color: '#a78bfa', data: {} },
      ],
      edges: [] },
    risk: {
      nodes: [
        { id: 'risk-1', label: 'Interest Rate Risk', type: 'risk', color: '#f97316', data: { cl_type: 'govt_guarantee' } },
        { id: 'risk-2', label: 'Inflation Risk', type: 'risk', color: '#f97316', data: { cl_type: 'environmental' } },
      ],
      edges: [] },
    contractor: {
      nodes: [
        { id: 'contractor-1', label: 'Construction Corp A', type: 'contractor', color: '#10b981', data: {} },
      ],
      edges: [] },
    portfolio: {
      nodes: [
        { id: 'port-1', label: 'Sovereign Debt Portfolio', type: 'portfolio', color: '#6366f1', data: {} },
      ],
      edges: [] } };

  const results: Record<string, { nodes: KGNode[]; edges: KGEdge[] }> = {};
  const matchedTypes: KGNodeType[] = [];

  for (const type of nodeTypes) {
    const key = type;
    if (mockResults[key]) {
      results[key] = mockResults[key];
      matchedTypes.push(type);
    }
  }

  const allNodes: KGNode[] = Object.values(results)
    .flatMap((r) => r.nodes)
    .slice(0, 30)
    .map((n, i) => ({
      x: 150 + ((i * 97) % 600),
      y: 120 + ((i * 53) % 360),
      vx: 0,
      vy: 0,
      radius: 14,
      ...n }));
  const allEdges: KGEdge[] = Object.values(results)
    .flatMap((r) => r.edges)
    .slice(0, 30);

  return {
    success: true,
    data: {
      nodes: allNodes,
      edges: allEdges,
      total: allNodes.length } };
}

const MOCK_DATA: KGData = {
  nodes: [
    { id: 'port-1', label: 'Sovereign Debt Portfolio', type: 'portfolio', x: 450, y: 300, vx: 0, vy: 0, radius: 22, color: '#6366f1' },
    { id: 'agency-1', label: 'Treasury Department', type: 'agency', x: 300, y: 200, vx: 0, vy: 0, radius: 18, color: '#06b6d4' },
    { id: 'debt-1', label: 'US Treasury 10Y', type: 'instrument', x: 600, y: 220, vx: 0, vy: 0, radius: 16, color: '#22d3ee' },
  ],
  edges: [
    { source: 'agency-1', target: 'debt-1', label: 'issued_by', weight: 1, type: 'issued_by' },
    { source: 'port-1', target: 'debt-1', label: 'holds', weight: 1, type: 'holds' },
  ] };

export default function KnowledgeGraph() {
  const svgRef = useRef<SVGSVGElement>(null);
  const [mockMode] = useState(useMock);
  const [data, setData] = useState<KGData>(MOCK_DATA);
  const [selectedNode, setSelectedNode] = useState<KGNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [filter, setFilter] = useState<Set<KGNodeType>>(new Set(['portfolio', 'instrument', 'currency', 'counterparty', 'scenario', 'strategy']));
  const [isDragging, setIsDragging] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [search, setSearch] = useState<SearchState>({
    query: '',
    nodeTypes: ['policy', 'agency', 'project', 'debt_issuance', 'budget', 'risk', 'contractor'],
    loading: false,
    error: null });

  // Search handler - uses mockAdapter when in mock mode
  const handleSearch = useCallback(async () => {
    if (!search.query.trim()) {
      setSearch(prev => ({ ...prev, loading: false, error: 'Enter a search query' }));
      return;
    }
    setSearch(prev => ({ ...prev, loading: true, error: null }));
    try {
      const result = mockMode
        ? await mockAdapter.knowledgeGraph.search(search.query, search.nodeTypes)
        : await searchKnowledgeGraphApi(
            search.query,
            search.nodeTypes,
            { nodeTypes: search.nodeTypes, nameContains: search.query }
          );
      if (result.success && result.data) {
        setSearch(prev => ({ ...prev, loading: false, data: result.data }));
        // Update graph data with search results
        setData(prev => ({
          ...prev,
          nodes: result.data.nodes,
          edges: result.data.edges }));
      } else {
        const message = !result.success && 'error' in result && result.error
          ? result.error
          : 'Search failed';
        setSearch(prev => ({ ...prev, loading: false, error: message }));
      }
    } catch (err) {
      setSearch(prev => ({ ...prev, loading: false, error: 'Search request failed' }));
    }
  }, [search.query, search.nodeTypes, mockMode]);

  // Run search on query change with delay
  useEffect(() => {
    const timeoutId = setTimeout(handleSearch, 300);
    return () => clearTimeout(timeoutId);
  }, [handleSearch, search.query]);

  // Force-simulation step shared by the layout effect and animation loop
  const animationRef = useRef<number>(0);
  const simulate = useCallback(() => {
    const nodes = data.nodes;
    const edges = data.edges;
    const alpha = 0.3;
    const repulsion = 5000;
    const attraction = 0.01;
    const centerGravity = 0.005;
    const centerX = 450;
    const centerY = 300;

    // Apply forces
    for (let i = 0; i < nodes.length; i++) {
      let fx = 0;
      let fy = 0;

      // Repulsion from other nodes
      for (let j = 0; j < nodes.length; j++) {
        if (i === j) continue;
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = repulsion / (dist * dist);
        fx += (dx / dist) * force;
        fy += (dy / dist) * force;
      }

      // Attraction along edges
      for (const edge of edges) {
        let other: KGNode | null = null;
        if (edge.source === nodes[i].id) {
          other = nodes.find(n => n.id === edge.target) || null;
        } else if (edge.target === nodes[i].id) {
          other = nodes.find(n => n.id === edge.source) || null;
        }
        if (other) {
          const dx = other.x - nodes[i].x;
          const dy = other.y - nodes[i].y;
          fx += dx * attraction * edge.weight;
          fy += dy * attraction * edge.weight;
        }
      }

      // Center gravity
      fx += (centerX - nodes[i].x) * centerGravity;
      fy += (centerY - nodes[i].y) * centerGravity;

      // Apply forces (skip dragged node)
      if (isDragging !== nodes[i].id) {
        nodes[i].vx = (nodes[i].vx + fx * alpha) * 0.9;
        nodes[i].vy = (nodes[i].vy + fy * alpha) * 0.9;
        nodes[i].x += nodes[i].vx;
        nodes[i].y += nodes[i].vy;
      }
    }
  }, [data, isDragging]);

  // Animation loop
  useEffect(() => {
    let running = true;
    const tick = () => {
      if (!running) return;
      simulate();
      animationRef.current = requestAnimationFrame(tick);
    };
    animationRef.current = requestAnimationFrame(tick);
    return () => {
      running = false;
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [simulate]);

  // Mouse handlers
  const handleMouseDown = (nodeId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const node = data.nodes.find(n => n.id === nodeId);
    if (!node) return;
    setIsDragging(nodeId);
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    setDragOffset({
      x: (e.clientX - rect.left) / zoom - pan.x - node.x,
      y: (e.clientY - rect.top) / zoom - pan.y - node.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const node = data.nodes.find(n => n.id === isDragging);
    if (!node) return;
    node.x = (e.clientX - rect.left) / zoom - pan.x - dragOffset.x;
    node.y = (e.clientY - rect.top) / zoom - pan.y - dragOffset.y;
    node.vx = 0;
    node.vy = 0;
  };

  const handleMouseUp = () => {
    setIsDragging(null);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom(z => Math.min(3, Math.max(0.3, z * delta)));
  };

  const toggleFilter = (type: KGNodeType) => {
    setFilter(prev => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  // Combined nodes: filter + search results
  const searchNodeIds = new Set(search.data?.nodes.map(n => n.id) || []);
  const allNodes = [...data.nodes, ...(search.data?.nodes || [])];
  const uniqueNodeIds = new Set([...allNodes.map(n => n.id)]);
  const uniqueNodes = allNodes.filter((n, i) => uniqueNodeIds.has(n.id) && i === allNodes.findIndex((nn) => nn.id === n.id));
  const filteredNodes = uniqueNodes.filter(n => search.query ? true : filter.has(n.type));
  const filteredNodeIds = new Set(filteredNodes.map(n => n.id));
  const filteredEdges = data.edges.filter(e => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target));
  // Also include edges from search data
  const searchEdges = search.data?.edges || [];
  const mergedEdges = [...filteredEdges, ...searchEdges].filter(
    (e, i, arr) => arr.findIndex((ee) => ee.source === e.source && ee.target === e.target) === i
  );

  // Get connected nodes for selected/hovered
  const connectedIds = new Set<string>();
  if (selectedNode || hoveredNode) {
    const activeId = hoveredNode || selectedNode?.id;
    if (activeId) {
      data.edges.forEach(e => {
        if (e.source === activeId) connectedIds.add(e.target);
        if (e.target === activeId) connectedIds.add(e.source);
      });
    }
  }

  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl flex items-center justify-center">
            <span className="text-lg">🕸️</span>
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Knowledge Graph</h2>
            <p className="text-sm text-slate-400">Interactive relationship map across portfolios, instruments, and entities</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setZoom(z => Math.min(3, z * 1.2))} className="px-2 py-1 bg-white/10 rounded text-sm text-white">+</button>
          <button onClick={() => setZoom(z => Math.max(0.3, z * 0.8))} className="px-2 py-1 bg-white/10 rounded text-sm text-white">−</button>
          <button onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }} className="px-2 py-1 bg-white/10 rounded text-xs text-slate-400">Reset</button>
        </div>
      </div>

      {/* Search */}
      <div className="flex items-center gap-2">
        <input
          type="text"
          placeholder="Search nodes..."
          value={search.query}
          onChange={(e) => setSearch({ ...search, query: e.target.value })}
          className="flex-1 rounded-lg border border-slate-600 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-colors"
        />
        <button
          onClick={() => setSearch(prev => ({ ...prev, loading: true }))}
          disabled={search.loading}
          className="px-4 py-2 rounded-lg bg-cyan-600 text-white text-sm hover:bg-cyan-500 transition-colors disabled:opacity-50"
        >
          {search.loading ? <><span className="animate-spin inline-block mr-2"/> Searching...</> : <><svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"><path d="M9.5 3.16l.713.713a5.5 5.5 0 0 1 7.777 7.777l-.713.713a5.5 5.5 0 0 1-7.777-7.777L9.5 3.16zm.146 6.02a1 1 0 0 1 1.414 0l1.413 1.414a1 1 0 0 1-1.414 1.414l-1.413-1.414a1 1 0 0 1 0-1.414zM12 2a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h2.293l.354.359L15 8.293l1.414-1.414A2 2 0 0 1 12 2z"/></svg> Search</>}
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {(['portfolio', 'instrument', 'currency', 'counterparty', 'scenario', 'strategy'] as const).map(type => (
          <button
            key={type}
            onClick={() => toggleFilter(type)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              filter.has(type)
                ? 'text-white border'
                : 'bg-white/5 text-slate-500 border border-transparent'
            }`}
            style={filter.has(type) ? { backgroundColor: `${NODE_COLORS[type]}20`, borderColor: `${NODE_COLORS[type]}40`, color: NODE_COLORS[type] } : {}}
          >
            {NODE_ICONS[type]} {type.charAt(0).toUpperCase() + type.slice(1)}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Graph */}
        <div className="lg:col-span-3 glass rounded-2xl overflow-hidden" style={{ height: '600px' }}>
          <svg
            ref={svgRef}
            width="100%"
            height="100%"
            viewBox="0 0 900 600"
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
            className="cursor-grab active:cursor-grabbing"
          >
            <defs>
              <filter id="glow">
                <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                <feMerge>
                  <feMergeNode in="coloredBlur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              <radialGradient id="nodeGlow" cx="30%" cy="30%">
                <stop offset="0%" stopColor="white" stopOpacity="0.3" />
                <stop offset="100%" stopColor="white" stopOpacity="0" />
              </radialGradient>
            </defs>

            <g transform={`scale(${zoom}) translate(${pan.x}, ${pan.y})`}>
              {/* Edges */}
              {mergedEdges.map((edge, i) => {
                const source = data.nodes.find(n => n.id === edge.source);
                const target = data.nodes.find(n => n.id === edge.target);
                if (!source || !target) return null;
                
                const isActive = hoveredNode === edge.source || hoveredNode === edge.target ||
                                  selectedNode?.id === edge.source || selectedNode?.id === edge.target;
                
                return (
                  <g key={i}>
                    <line
                      x1={source.x}
                      y1={source.y}
                      x2={target.x}
                      y2={target.y}
                      stroke={EDGE_COLORS[edge.type]}
                      strokeWidth={edge.weight * (isActive ? 2 : 1)}
                      strokeOpacity={isActive ? 0.8 : 0.2}
                      strokeDasharray={String(edge.type) === 'affected_by' ? '5,5' : undefined}
                    />
                    {isActive && (
                      <text
                        x={(source.x + target.x) / 2}
                        y={(source.y + target.y) / 2}
                        fill={EDGE_COLORS[edge.type]}
                        fontSize="9"
                        textAnchor="middle"
                        dominantBaseline="middle"
                      >
                        {edge.label}
                      </text>
                    )}
                  </g>
                );
              })}

              {/* Nodes */}
              {filteredNodes.map(node => {
                const isSelected = selectedNode?.id === node.id;
                const isHovered = hoveredNode === node.id;
                const isConnected = connectedIds.has(node.id);
                const isDimmed = (selectedNode || hoveredNode) && !isSelected && !isHovered && !isConnected;

                return (
                  <g
                    key={node.id}
                    transform={`translate(${node.x}, ${node.y})`}
                    onMouseDown={(e) => handleMouseDown(node.id, e)}
                    onMouseEnter={() => setHoveredNode(node.id)}
                    onMouseLeave={() => setHoveredNode(null)}
                    onClick={() => setSelectedNode(isSelected ? null : node)}
                    style={{ cursor: isDragging === node.id ? 'grabbing' : 'pointer', opacity: isDimmed ? 0.3 : 1 }}
                  >
                    {/* Glow ring */}
                    {(isSelected || isHovered) && (
                      <circle
                        r={node.radius + 8}
                        fill="none"
                        stroke={node.color}
                        strokeWidth="2"
                        strokeOpacity="0.4"
                        filter="url(#glow)"
                      />
                    )}
                    {/* Main circle */}
                    <circle
                      r={node.radius}
                      fill={`${node.color}30`}
                      stroke={node.color}
                      strokeWidth={isSelected ? 3 : 1.5}
                    />
                    {/* Inner highlight */}
                    <circle r={node.radius * 0.7} fill="url(#nodeGlow)" />
                    {/* Icon */}
                    <text
                      fontSize={node.radius * 0.7}
                      textAnchor="middle"
                      dominantBaseline="middle"
                    >
                      {NODE_ICONS[node.type]}
                    </text>
                    {/* Label */}
                    <text
                      y={node.radius + 14}
                      fill="white"
                      fontSize="10"
                      textAnchor="middle"
                      fontWeight={isSelected ? 'bold' : 'normal'}
                    >
                      {node.label}
                    </text>
                  </g>
                );
              })}
            </g>
          </svg>
        </div>

        {/* Detail Panel */}
        <div className="space-y-4">
          {selectedNode ? (
            <div className="glass rounded-2xl p-5 space-y-4">
              <div className="flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center text-lg"
                  style={{ backgroundColor: `${selectedNode.color}30` }}
                >
                  {NODE_ICONS[selectedNode.type]}
                </div>
                <div>
                  <h3 className="text-white font-bold">{selectedNode.label}</h3>
                  <p className="text-xs text-slate-400 capitalize">{selectedNode.type}</p>
                </div>
              </div>

              {/* Properties */}
              {selectedNode.data && (
                <div className="space-y-2">
                  <h4 className="text-xs font-medium text-slate-500 uppercase">Properties</h4>
                  {Object.entries(selectedNode.data).map(([key, value]) => (
                    <div key={key} className="flex justify-between text-sm">
                      <span className="text-slate-400 capitalize">{key.replace(/([A-Z])/g, ' $1')}</span>
                      <span className="text-white">{String(value)}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Connections */}
              <div className="space-y-2">
                <h4 className="text-xs font-medium text-slate-500 uppercase">Connections</h4>
                {data.edges
                  .filter(e => e.source === selectedNode.id || e.target === selectedNode.id)
                  .map((edge, i) => {
                    const otherId = edge.source === selectedNode.id ? edge.target : edge.source;
                    const other = data.nodes.find(n => n.id === otherId);
                    if (!other) return null;
                    return (
                      <button
                        key={i}
                        onClick={() => setSelectedNode(other)}
                        className="w-full flex items-center gap-2 px-3 py-2 bg-white/5 rounded-lg hover:bg-white/10 transition-colors text-left"
                      >
                        <span className="text-sm">{NODE_ICONS[other.type]}</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-white truncate">{other.label}</p>
                          <p className="text-xs text-slate-500">{edge.label}</p>
                        </div>
                        <div
                          className="w-2 h-2 rounded-full flex-shrink-0"
                          style={{ backgroundColor: NODE_COLORS[other.type] }}
                        />
                      </button>
                    );
                  })}
              </div>

              <button
                onClick={() => setSelectedNode(null)}
                className="w-full py-2 bg-white/5 rounded-lg text-xs text-slate-400 hover:bg-white/10 transition-colors"
              >
                Deselect
              </button>
            </div>
          ) : (
            <div className="glass rounded-2xl p-5 text-center">
              <div className="text-3xl mb-3">🕸️</div>
              <h3 className="text-white font-medium mb-1">Select a Node</h3>
              <p className="text-xs text-slate-400">Click any node to see its properties and connections</p>
            </div>
          )}

          {/* Legend */}
          <div className="glass rounded-2xl p-4">
            <h4 className="text-xs font-medium text-slate-500 mb-3">Edge Types</h4>
            <div className="space-y-2">
              {Object.entries(EDGE_COLORS).map(([type, color]) => (
                <div key={type} className="flex items-center gap-2">
                  <div className="w-6 h-0.5 rounded" style={{ backgroundColor: color }} />
                  <span className="text-xs text-slate-400 capitalize">{type.replace(/_/g, ' ')}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Stats */}
<div className="glass rounded-2xl p-4">
              <h4 className="text-xs font-medium text-slate-500 mb-3">Graph Stats</h4>
              <div className="grid grid-cols-2 gap-2 text-center">
                <div>
                  <p className="text-lg font-bold text-white">{filteredNodes.length}</p>
                  <p className="text-xs text-slate-500">Nodes</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-white">{mergedEdges.length}</p>
                  <p className="text-xs text-slate-500">Edges</p>
                </div>
              </div>
              {search.query && (
                <div className="mt-2 p-2 bg-cyan-500/10 rounded border border-cyan-500/20 text-xs text-cyan-400">
                  <p className="font-medium">Search: {search.query}</p>
                  <p className="text-slate-500">{(search.data?.total || 0)} results</p>
                </div>
              )}
            </div>
        </div>
      </div>
    </div>
  );
}
