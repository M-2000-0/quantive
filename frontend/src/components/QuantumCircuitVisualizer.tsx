import { useState, useMemo, useCallback } from 'react';

// ── Types ─────────────────────────────────────────────────────────────

export interface Gate {
  gate: string;
  qubit: number;
  param?: number;
  control?: number;
  target?: number;
  power?: number;
  layer?: number;
  classical?: number;
  qubit_a?: number;
  qubit_b?: number;
}

interface GateInfo {
  name: string;
  color: string;
  bg: string;
  borderColor: string;
  description: string;
  symbol: string;
}

interface TooltipState {
  gate: Gate;
  info: GateInfo;
  x: number;
  y: number;
  visible: boolean;
}

// ── Gate registry ─────────────────────────────────────────────────────

const GATE_REGISTRY: Record<string, GateInfo> = {
  h: { name: 'Hadamard', color: '#60a5fa', bg: 'rgba(96,165,250,0.15)', borderColor: '#3b82f6', description: 'Equal superposition', symbol: 'H' },
  x: { name: 'Pauli-X', color: '#f87171', bg: 'rgba(248,113,113,0.15)', borderColor: '#ef4444', description: 'Bit flip (NOT)', symbol: 'X' },
  y: { name: 'Pauli-Y', color: '#c084fc', bg: 'rgba(192,132,252,0.15)', borderColor: '#a855f7', description: 'Y rotation', symbol: 'Y' },
  z: { name: 'Pauli-Z', color: '#34d399', bg: 'rgba(52,211,153,0.15)', borderColor: '#10b981', description: 'Phase flip', symbol: 'Z' },
  rx: { name: 'Rx', color: '#fb923c', bg: 'rgba(251,146,60,0.15)', borderColor: '#f97316', description: 'X rotation', symbol: 'Rx' },
  ry: { name: 'Ry', color: '#fb923c', bg: 'rgba(251,146,60,0.15)', borderColor: '#f97316', description: 'Y rotation', symbol: 'Ry' },
  rz: { name: 'Rz', color: '#fb923c', bg: 'rgba(251,146,60,0.15)', borderColor: '#f97316', description: 'Z rotation', symbol: 'Rz' },
  cx: { name: 'CNOT', color: '#a78bfa', bg: 'rgba(167,139,250,0.15)', borderColor: '#8b5cf6', description: 'Controlled-NOT', symbol: '⊕' },
  cz: { name: 'CZ', color: '#a78bfa', bg: 'rgba(167,139,250,0.15)', borderColor: '#8b5cf6', description: 'Controlled-Z', symbol: 'CZ' },
  cp: { name: 'CP', color: '#a78bfa', bg: 'rgba(167,139,250,0.15)', borderColor: '#8b5cf6', description: 'Controlled Phase', symbol: 'CP' },
  swap: { name: 'SWAP', color: '#fbbf24', bg: 'rgba(251,191,36,0.15)', borderColor: '#f59e0b', description: 'Swap qubits', symbol: 'swap' },
  measure: { name: 'Measure', color: '#94a3b8', bg: 'rgba(148,163,184,0.15)', borderColor: '#64748b', description: 'Measurement', symbol: 'M' },
  controlled_grover: { name: 'Ctrl-Grover', color: '#06b6d4', bg: 'rgba(6,182,212,0.15)', borderColor: '#0891b2', description: 'Controlled Grover iteration', symbol: 'Q' } };

const DEFAULT_GATE: GateInfo = { name: 'Unknown', color: '#6b7280', bg: 'rgba(107,114,128,0.1)', borderColor: '#4b5563', description: 'Unknown gate', symbol: '?' };

function getGateInfo(gate: string): GateInfo {
  return GATE_REGISTRY[gate] || DEFAULT_GATE;
}

// ── Layout constants ──────────────────────────────────────────────────

const ROW_HEIGHT = 48;
const GATE_WIDTH = 44;
const GATE_HEIGHT = 36;
const LAYER_SPACING = 60;
const LEFT_PADDING = 80;
const TOP_PADDING = 20;
const RIGHT_PADDING = 40;
const BOTTOM_PADDING = 30;

// ── Helper: parse QASM text into Gate[] ──────────────────────────────

export function parseQASMToGates(qasm: string, numQubits: number): Gate[] {
  const gates: Gate[] = [];
  const lines = qasm.split('\n');

  let layer = 0;
  const qubitLastLayer: Record<number, number> = {};

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line || line.startsWith('//') || line.startsWith('OPENQASM') || line.startsWith('include') || line.startsWith('qubit') || line.startsWith('bit') || line.startsWith('angle')) {
      continue;
    }

    if (line === 'c = measure q;') {
      for (let q = 0; q < numQubits; q++) {
        const l = (qubitLastLayer[q] ?? -1) + 1;
        gates.push({ gate: 'measure', qubit: q, classical: q, layer: l });
        qubitLastLayer[q] = l;
      }
      continue;
    }

    // Parse single-qubit gates: h q[0], ry(theta) q[0], rz(0.5) q[1]
    const singleMatch = line.match(/^([a-z]+)(?:\(([^)]+)\))?\s+q\[(\d+)\]/);
    if (singleMatch) {
      const [, gateName, paramStr, qubitStr] = singleMatch;
      const qubit = parseInt(qubitStr);
      const l = (qubitLastLayer[qubit] ?? -1) + 1;
      gates.push({
        gate: gateName,
        qubit,
        param: paramStr ? parseFloat(paramStr) : undefined,
        layer: l });
      qubitLastLayer[qubit] = l;
      continue;
    }

    // Parse two-qubit gates: cx q[0], q[1] / cz q[0], q[1]
    const twoMatch = line.match(/^([a-z]+)(?:\(([^)]+)\))?\s+q\[(\d+)\]\s*,\s*q\[(\d+)\]/);
    if (twoMatch) {
      const [, gateName, paramStr, ctrlStr, tgtStr] = twoMatch;
      const control = parseInt(ctrlStr);
      const target = parseInt(tgtStr);
      const l = Math.max(qubitLastLayer[control] ?? -1, qubitLastLayer[target] ?? -1) + 1;
      gates.push({
        gate: gateName,
        qubit: control,
        control,
        target,
        param: paramStr ? parseFloat(paramStr) : undefined,
        layer: l });
      qubitLastLayer[control] = l;
      qubitLastLayer[target] = l;
      continue;
    }

    // Parse swap: swap q[0], q[1]
    const swapMatch = line.match(/^swap\s+q\[(\d+)\]\s*,\s*q\[(\d+)\]/);
    if (swapMatch) {
      const a = parseInt(swapMatch[1]);
      const b = parseInt(swapMatch[2]);
      const l = Math.max(qubitLastLayer[a] ?? -1, qubitLastLayer[b] ?? -1) + 1;
      gates.push({ gate: 'swap', qubit: a, qubit_a: a, qubit_b: b, layer: l });
      qubitLastLayer[a] = l;
      qubitLastLayer[b] = l;
      continue;
    }

    // Parse measurement: c[0] = measure q[0]
    const measMatch = line.match(/^c\[(\d+)\]\s*=\s*measure\s+q\[(\d+)\]/);
    if (measMatch) {
      const classical = parseInt(measMatch[1]);
      const qubit = parseInt(measMatch[2]);
      const l = (qubitLastLayer[qubit] ?? -1) + 1;
      gates.push({ gate: 'measure', qubit, classical, layer: l });
      qubitLastLayer[qubit] = l;
      continue;
    }

    // Parse controlled grover comment: [controlled_grover power=4 ctrl=0 tgt=4]
    const ctrlGroverMatch = line.match(/\[controlled_grover\s+power=(\d+)\s+ctrl=(\d+)\s+tgt=(\d+)\]/);
    if (ctrlGroverMatch) {
      const ctrl = parseInt(ctrlGroverMatch[2]);
      const tgt = parseInt(ctrlGroverMatch[3]);
      const l = Math.max(qubitLastLayer[ctrl] ?? -1, qubitLastLayer[tgt] ?? -1) + 1;
      gates.push({ gate: 'controlled_grover', qubit: ctrl, control: ctrl, target: tgt, power: parseInt(ctrlGroverMatch[1]), layer: l });
      qubitLastLayer[ctrl] = l;
      qubitLastLayer[tgt] = l;
    }
  }

  return gates;
}

// ── Main Component ────────────────────────────────────────────────────

interface QuantumCircuitVisualizerProps {
  gates: Gate[];
  numQubits: number;
  height?: number;
  className?: string;
}

export default function QuantumCircuitVisualizer({
  gates,
  numQubits,
  height,
  className = '' }: QuantumCircuitVisualizerProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const [selectedGate, setSelectedGate] = useState<Gate | null>(null);
  const [hoveredQubit, setHoveredQubit] = useState<number | null>(null);

  // Compute layout
  const { layers, maxLayer, svgWidth, svgHeight } = useMemo(() => {
    let maxL = 0;
    for (const g of gates) {
      if (g.layer !== undefined && g.layer > maxL) maxL = g.layer;
    }
    const layers = maxL + 1;
    const svgWidth = LEFT_PADDING + layers * LAYER_SPACING + RIGHT_PADDING;
    const svgH = TOP_PADDING + numQubits * ROW_HEIGHT + BOTTOM_PADDING;
    return { layers, maxLayer: maxL, svgWidth, svgHeight: height || svgH };
  }, [gates, numQubits, height]);

  const gateAtPosition = useMemo(() => {
    const map = new Map<string, Gate>();
    for (const g of gates) {
      const key = `${g.layer}-${g.control ?? g.qubit ?? g.qubit_a}`;
      map.set(key, g);
    }
    return map;
  }, [gates]);

  const handleGateHover = useCallback((gate: Gate, e: React.MouseEvent) => {
    const rect = (e.currentTarget as SVGElement).getBoundingClientRect();
    setTooltip({
      gate,
      info: getGateInfo(gate.gate),
      x: rect.left + rect.width / 2,
      y: rect.top - 8,
      visible: true });
  }, []);

  const handleGateClick = useCallback((gate: Gate) => {
    setSelectedGate(prev => prev === gate ? null : gate);
  }, []);

  return (
    <div className={`relative ${className}`}>
      {/* Gate info panel */}
      {selectedGate && (
        <div className="absolute top-2 right-2 z-20 glass p-3 rounded-lg border border-white/10 min-w-[180px]">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-6 h-6 rounded flex items-center justify-center text-xs font-bold"
              style={{ backgroundColor: getGateInfo(selectedGate.gate).bg, color: getGateInfo(selectedGate.gate).color, border: `1px solid ${getGateInfo(selectedGate.gate).borderColor}` }}>
              {getGateInfo(selectedGate.gate).symbol}
            </div>
            <div>
              <div className="text-xs font-semibold text-white/90">{getGateInfo(selectedGate.gate).name}</div>
              <div className="text-[10px] text-white/40">{getGateInfo(selectedGate.gate).description}</div>
            </div>
          </div>
          <div className="space-y-1 text-[10px]">
            {selectedGate.qubit !== undefined && (
              <div className="flex justify-between"><span className="text-white/40">Qubit</span><span className="text-white/70">{selectedGate.qubit}</span></div>
            )}
            {selectedGate.param !== undefined && (
              <div className="flex justify-between"><span className="text-white/40">Parameter</span><span className="text-white/70">{selectedGate.param.toFixed(4)} rad</span></div>
            )}
            {selectedGate.control !== undefined && (
              <div className="flex justify-between"><span className="text-white/40">Control</span><span className="text-white/70">q[{selectedGate.control}]</span></div>
            )}
            {selectedGate.target !== undefined && (
              <div className="flex justify-between"><span className="text-white/40">Target</span><span className="text-white/70">q[{selectedGate.target}]</span></div>
            )}
            {selectedGate.power !== undefined && (
              <div className="flex justify-between"><span className="text-white/40">Power</span><span className="text-white/70">Q^{selectedGate.power}</span></div>
            )}
            {selectedGate.layer !== undefined && (
              <div className="flex justify-between"><span className="text-white/40">Layer</span><span className="text-white/70">{selectedGate.layer}</span></div>
            )}
          </div>
          <button onClick={() => setSelectedGate(null)}
            className="mt-2 text-[10px] text-white/30 hover:text-white/60">dismiss</button>
        </div>
      )}

      <svg
        width="100%"
        height={svgHeight}
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        className="bg-transparent select-none"
        style={{ minHeight: 200 }}
      >
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Qubit wires */}
        {Array.from({ length: numQubits }, (_, q) => {
          const y = TOP_PADDING + q * ROW_HEIGHT + GATE_HEIGHT / 2;
          const isHovered = hoveredQubit === q;
          return (
            <g key={`qwire-${q}`} onMouseEnter={() => setHoveredQubit(q)} onMouseLeave={() => setHoveredQubit(null)}>
              {/* Qubit label */}
              <text x={10} y={y + 4} fontSize={11} fill={isHovered ? 'rgba(148,163,184,0.9)' : 'rgba(148,163,184,0.4)'} fontFamily="monospace">
                |q{q}⟩
              </text>
              {/* Wire */}
              <line
                x1={LEFT_PADDING - 20} y1={y}
                x2={svgWidth - 10} y2={y}
                stroke={isHovered ? 'rgba(148,163,184,0.3)' : 'rgba(148,163,184,0.08)'}
                strokeWidth={isHovered ? 1.5 : 1}
                strokeDasharray={isHovered ? 'none' : '4 4'}
              />
            </g>
          );
        })}

        {/* Gates */}
        {gates.map((gate, idx) => {
          const layer = gate.layer ?? 0;
          const x = LEFT_PADDING + layer * LAYER_SPACING;
          const info = getGateInfo(gate.gate);

          // Handle swap gates specially
          if (gate.gate === 'swap' && gate.qubit_a !== undefined && gate.qubit_b !== undefined) {
            const yA = TOP_PADDING + gate.qubit_a * ROW_HEIGHT + GATE_HEIGHT / 2;
            const yB = TOP_PADDING + gate.qubit_b * ROW_HEIGHT + GATE_HEIGHT / 2;
            return (
              <g key={`gate-${idx}`}>
                <line x1={x} y1={yA} x2={x} y2={yB} stroke={info.borderColor} strokeWidth={1.5} />
                <text x={x} y={yA + 5} fontSize={14} fill={info.color} textAnchor="middle" fontFamily="monospace">×</text>
                <text x={x} y={yB + 5} fontSize={14} fill={info.color} textAnchor="middle" fontFamily="monospace">×</text>
              </g>
            );
          }

          // Handle measurement
          if (gate.gate === 'measure') {
            const y = TOP_PADDING + (gate.qubit ?? 0) * ROW_HEIGHT + GATE_HEIGHT / 2;
            return (
              <g key={`gate-${idx}`}
                onMouseEnter={(e) => handleGateHover(gate, e)}
                onMouseLeave={() => setTooltip(null)}
                onClick={() => handleGateClick(gate)}
                className="cursor-pointer"
              >
                <rect x={x - GATE_WIDTH / 2} y={y - GATE_HEIGHT / 2} width={GATE_WIDTH} height={GATE_HEIGHT}
                  rx={4} fill={info.bg} stroke={info.borderColor} strokeWidth={1} />
                {/* Meter arc */}
                <path d={`M ${x - 10} ${y + 6} A 12 12 0 0 1 ${x + 10} ${y + 6}`} fill="none" stroke={info.color} strokeWidth={1.5} />
                <line x1={x} y1={y + 6} x2={x + 6} y2={y - 8} stroke={info.color} strokeWidth={1.5} />
                <text x={x} y={y - GATE_HEIGHT / 2 - 4} fontSize={9} fill="rgba(148,163,184,0.4)" textAnchor="middle">
                  M{gate.classical ?? gate.qubit}
                </text>
              </g>
            );
          }

          // Controlled gate (CNOT, CZ, CP, controlled_grover)
          if (gate.control !== undefined && gate.target !== undefined) {
            const yCtrl = TOP_PADDING + gate.control * ROW_HEIGHT + GATE_HEIGHT / 2;
            const yTgt = TOP_PADDING + gate.target * ROW_HEIGHT + GATE_HEIGHT / 2;
            return (
              <g key={`gate-${idx}`}
                onMouseEnter={(e) => handleGateHover(gate, e)}
                onMouseLeave={() => setTooltip(null)}
                onClick={() => handleGateClick(gate)}
                className="cursor-pointer"
              >
                {/* Connection line */}
                <line x1={x} y1={yCtrl} x2={x} y2={yTgt}
                  stroke={info.borderColor} strokeWidth={1.5} opacity={0.6} />
                {/* Control dot */}
                <circle cx={x} cy={yCtrl} r={5} fill={info.color} filter="url(#glow)" />
                {/* Target box */}
                <rect x={x - GATE_WIDTH / 2} y={yTgt - GATE_HEIGHT / 2} width={GATE_WIDTH} height={GATE_HEIGHT}
                  rx={6} fill={info.bg} stroke={info.borderColor} strokeWidth={1.5} />
                {gate.gate === 'cx' ? (
                  <>
                    <line x1={x - GATE_WIDTH / 2} y1={yTgt} x2={x + GATE_WIDTH / 2} y2={yTgt} stroke={info.color} strokeWidth={1.5} />
                    <line x1={x} y1={yTgt - GATE_HEIGHT / 2} x2={x} y2={yTgt + GATE_HEIGHT / 2} stroke={info.color} strokeWidth={1.5} />
                  </>
                ) : (
                  <text x={x} y={yTgt + 5} fontSize={11} fill={info.color} textAnchor="middle" fontWeight="bold" fontFamily="monospace">
                    {info.symbol}
                  </text>
                )}
                {gate.power !== undefined && (
                  <text x={x + GATE_WIDTH / 2 + 4} y={yTgt + 4} fontSize={8} fill={info.color} opacity={0.6}>
                    ×{gate.power}
                  </text>
                )}
              </g>
            );
          }

          // Single-qubit gate
          const y = TOP_PADDING + (gate.qubit ?? 0) * ROW_HEIGHT + GATE_HEIGHT / 2;
          const displayText = gate.param !== undefined
            ? `${info.symbol}${gate.param !== undefined ? (gate.param / Math.PI).toFixed(1) + 'π' : ''}`
            : info.symbol;

          return (
            <g key={`gate-${idx}`}
              onMouseEnter={(e) => handleGateHover(gate, e)}
              onMouseLeave={() => setTooltip(null)}
              onClick={() => handleGateClick(gate)}
              className="cursor-pointer"
            >
              <rect x={x - GATE_WIDTH / 2} y={y - GATE_HEIGHT / 2} width={GATE_WIDTH} height={GATE_HEIGHT}
                rx={6} fill={info.bg} stroke={info.borderColor} strokeWidth={1.5} />
              <text x={x} y={y + 5} fontSize={11} fill={info.color} textAnchor="middle" fontWeight="bold" fontFamily="monospace">
                {displayText}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Floating tooltip */}
      {tooltip?.visible && (
        <div
          className="fixed z-50 pointer-events-none px-2.5 py-1.5 rounded-lg text-xs border"
          style={{
            left: tooltip.x,
            top: tooltip.y,
            transform: 'translate(-50%, -100%)',
            background: 'rgba(15,23,42,0.95)',
            borderColor: tooltip.info.borderColor,
            color: tooltip.info.color,
            backdropFilter: 'blur(8px)' }}
        >
          <span className="font-semibold">{tooltip.info.name}</span>
          {tooltip.gate.param !== undefined && (
            <span className="text-white/50 ml-1">({tooltip.gate.param.toFixed(3)} rad)</span>
          )}
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-3 px-2">
        {Object.entries(GATE_REGISTRY).filter(([k]) => ['h', 'x', 'z', 'ry', 'cx', 'cz', 'swap', 'measure'].includes(k)).map(([key, info]) => (
          <div key={key} className="flex items-center gap-1.5">
            <div className="w-4 h-3 rounded-sm border" style={{ backgroundColor: info.bg, borderColor: info.borderColor }}>
              <span className="block text-center text-[7px] font-bold leading-3" style={{ color: info.color }}>{info.symbol}</span>
            </div>
            <span className="text-[10px] text-white/30">{info.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
