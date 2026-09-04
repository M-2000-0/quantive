import { useState } from 'react';

interface SankeyNode {
  id: string;
  label: string;
  color?: string;
}

interface SankeyLink {
  source: string;
  target: string;
  value: number;
}

interface GlassSankeyDiagramProps {
  nodes: SankeyNode[];
  links: SankeyLink[];
  height?: number;
  title?: string;
  formatValue?: (value: number) => string;
}

export default function GlassSankeyDiagram({
  nodes, links, height = 300, title, formatValue,
}: GlassSankeyDiagramProps) {
  const [hoveredLink, setHoveredLink] = useState<number | null>(null);

  const nodeColors = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#f97316'];
  const nodeMap = new Map(nodes.map((n, i) => [n.id, { ...n, color: n.color || nodeColors[i % nodeColors.length] }]));

  // Simple layout: arrange nodes in columns based on links
  const leftNodes = nodes.filter((n) => !links.some((l) => l.target === n.id));
  const rightNodes = nodes.filter((n) => !links.some((l) => l.source === n.id));
  const midNodes = nodes.filter((n) => !leftNodes.includes(n) && !rightNodes.includes(n));

  const columns = [leftNodes, midNodes.length > 0 ? midNodes : [], rightNodes].filter((c) => c.length > 0);

  const maxLinks = Math.max(...links.map((l) => l.value), 1);
  const totalValue = links.reduce((sum, l) => sum + l.value, 0);

  const svgWidth = 600;
  const svgHeight = height;
  const colWidth = svgWidth / columns.length;

  // Position nodes
  const nodePositions = new Map<string, { x: number; y: number; width: number; height: number }>();
  columns.forEach((col, ci) => {
    const colTotal = links
      .filter((l) => col.some((n) => n.id === l.source || n.id === l.target))
      .reduce((sum, l) => sum + l.value, 0) || 1;
    let yOffset = 20;

    col.forEach((node) => {
      const nodeValue = links
        .filter((l) => l.source === node.id || l.target === node.id)
        .reduce((sum, l) => sum + l.value, 0) || 1;
      const nodeHeight = Math.max(((nodeValue / colTotal) * (svgHeight - 40)), 16);
      const nodeWidth = 16;

      nodePositions.set(node.id, {
        x: ci * colWidth + (ci === 0 ? 10 : colWidth - 26),
        y: yOffset,
        width: nodeWidth,
        height: nodeHeight,
      });
      yOffset += nodeHeight + 4;
    });
  });

  // Generate link paths
  const linkPaths = links.map((link, idx) => {
    const sourcePos = nodePositions.get(link.source);
    const targetPos = nodePositions.get(link.target);
    if (!sourcePos || !targetPos) return null;

    const thickness = Math.max((link.value / maxLinks) * 20, 2);
    const sy = sourcePos.y + sourcePos.height / 2;
    const ty = targetPos.y + targetPos.height / 2;
    const sx = sourcePos.x + sourcePos.width;
    const tx = targetPos.x;

    return {
      idx,
      d: `M${sx},${sy} C${sx + (tx - sx) / 2},${sy} ${tx - (tx - sx) / 2},${ty} ${tx},${ty}`,
      thickness,
      sourceColor: nodeMap.get(link.source)?.color || '#3b82f6',
      targetColor: nodeMap.get(link.target)?.color || '#8b5cf6',
      link,
    };
  }).filter(Boolean);

  return (
    <div className="glass-card p-4">
      {title && <h3 className="text-sm font-semibold text-white/80 mb-3">{title}</h3>}
      <svg width="100%" viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="overflow-visible">
        <defs>
          {linkPaths.map((lp) => lp && (
            <linearGradient key={`grad-${lp.idx}`} id={`link-grad-${lp.idx}`} x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor={lp.sourceColor} stopOpacity={hoveredLink === lp.idx ? 0.7 : 0.3} />
              <stop offset="100%" stopColor={lp.targetColor} stopOpacity={hoveredLink === lp.idx ? 0.7 : 0.3} />
            </linearGradient>
          ))}
        </defs>

        {/* Links */}
        {linkPaths.map((lp) => lp && (
          <path
            key={lp.idx}
            d={lp.d}
            fill="none"
            stroke={`url(#link-grad-${lp.idx})`}
            strokeWidth={lp.thickness}
            onMouseEnter={() => setHoveredLink(lp.idx)}
            onMouseLeave={() => setHoveredLink(null)}
            style={{ cursor: 'pointer', transition: 'stroke-opacity 0.2s' }}
          />
        ))}

        {/* Nodes */}
        {Array.from(nodePositions.entries()).map(([nodeId, pos]) => {
          const node = nodeMap.get(nodeId);
          if (!node) return null;
          return (
            <g key={nodeId}>
              <rect x={pos.x} y={pos.y} width={pos.width} height={pos.height} rx={4} fill={node.color} fillOpacity={0.85} />
              <text
                x={pos.x + (pos.x < svgWidth / 2 ? pos.width + 6 : -6)}
                y={pos.y + pos.height / 2}
                dominantBaseline="middle"
                textAnchor={pos.x < svgWidth / 2 ? 'start' : 'end'}
                fill="rgba(255,255,255,0.7)"
                fontSize={11}
              >
                {node.label}
              </text>
            </g>
          );
        })}

        {/* Hover tooltip */}
        {hoveredLink !== null && linkPaths[hoveredLink] && (
          <text x={svgWidth / 2} y={15} textAnchor="middle" fill="rgba(255,255,255,0.8)" fontSize={12} fontWeight={600}>
            {linkPaths[hoveredLink]!.link.source} → {linkPaths[hoveredLink]!.link.target}: {formatValue ? formatValue(linkPaths[hoveredLink]!.link.value) : linkPaths[hoveredLink]!.link.value}
          </text>
        )}
      </svg>
    </div>
  );
}
