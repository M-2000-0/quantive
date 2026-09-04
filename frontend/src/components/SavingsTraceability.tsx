import React, { useState } from 'react';
import { DollarSign } from 'lucide-react';

interface TraceNode {
  label: string;
  value: string;
  percentage: number;
  children?: TraceNode[];
}

const TRACE_TREE: TraceNode = {
  label: 'Total Annual Savings',
  value: '$400M',
  percentage: 100,
  children: [
    {
      label: 'Maturity Extension Savings',
      value: '$180M',
      percentage: 45,
      children: [
        { label: '2027 Maturity Wall Avoided', value: '$120M', percentage: 30, children: [
          { label: 'Reduced emergency issuance premium', value: '$80M', percentage: 20 },
          { label: 'Avoided forced sale of assets', value: '$40M', percentage: 10 },
        ]},
        { label: 'Duration Optimization', value: '$60M', percentage: 15, children: [
          { label: 'Better entry points on long-end', value: '$35M', percentage: 8.75 },
          { label: 'Reduced rollover frequency', value: '$25M', percentage: 6.25 },
        ]},
      ] },
    {
      label: 'FX Hedging Savings',
      value: '$120M',
      percentage: 30,
      children: [
        { label: 'Reduced USD exposure from 41% to 23%', value: '$85M', percentage: 21.25 },
        { label: 'Optimized hedge ratios', value: '$35M', percentage: 8.75 },
      ] },
    {
      label: 'Coupon Optimization',
      value: '$65M',
      percentage: 16.25,
      children: [
        { label: 'Shifted to lower-coupon instruments', value: '$40M', percentage: 10 },
        { label: 'Green bond premium captured', value: '$25M', percentage: 6.25 },
      ] },
    {
      label: 'Operational Efficiency',
      value: '$35M',
      percentage: 8.75,
      children: [
        { label: 'Reduced transaction costs', value: '$20M', percentage: 5 },
        { label: 'Consolidated settlement', value: '$15M', percentage: 3.75 },
      ] },
  ] };

function TraceNodeComponent({ node, depth = 0 }: { node: TraceNode; depth?: number }) {
  const [expanded, setExpanded] = useState(depth < 1);
  const hasChildren = node.children && node.children.length > 0;

  return (
    <div style={{ marginLeft: depth * 24 }}>
      <button
        onClick={() => hasChildren && setExpanded(!expanded)}
        className={`w-full text-left flex items-center gap-3 p-3 rounded-xl transition-all hover:bg-white/5 ${hasChildren ? 'cursor-pointer' : 'cursor-default'}`}
      >
        {hasChildren && (
          <span className="text-slate-500 text-xs w-4">{expanded ? '▼' : '▶'}</span>
        )}
        {!hasChildren && <span className="w-4" />}
        <div className="flex-1">
          <span className="text-white text-sm">{node.label}</span>
        </div>
        <span className="text-white font-bold text-sm">{node.value}</span>
        <span className="text-slate-400 text-xs w-16 text-right">{node.percentage}%</span>
      </button>
      {expanded && hasChildren && (
        <div className="border-l border-white/10 ml-4">
          {node.children!.map((child, i) => (
            <TraceNodeComponent key={i} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function SavingsTraceability() {
  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-green-600 rounded-xl flex items-center justify-center">
          <DollarSign className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Savings Traceability</h2>
          <p className="text-sm text-slate-400">Explain every dollar — from $400M total to individual components</p>
        </div>
      </div>

      {/* Summary Banner */}
      <div className="bg-gradient-to-r from-emerald-500/10 to-green-500/10 border border-emerald-500/20 rounded-2xl p-6 text-center">
        <p className="text-5xl font-bold text-emerald-400 mb-2">$400M</p>
        <p className="text-sm text-slate-400">Total Estimated Annual Savings</p>
        <p className="text-xs text-slate-500 mt-1">Click any component below to trace the full savings chain</p>
      </div>

      {/* Traceability Tree */}
      <div className="glass rounded-2xl p-6">
        <h3 className="text-sm font-medium text-slate-400 mb-4">SAVINGS BREAKDOWN TREE</h3>
        <div className="space-y-1">
          <TraceNodeComponent node={TRACE_TREE} />
        </div>
      </div>

      {/* Visual Flow */}
      <div className="glass rounded-2xl p-6">
        <h3 className="text-sm font-medium text-slate-400 mb-4">SAVINGS FLOW</h3>
        <div className="flex items-center justify-center gap-3 flex-wrap">
          {[
            { label: '$400M Total', color: 'bg-emerald-500/20 text-emerald-400' },
            { label: '→', color: 'text-slate-500' },
            { label: '$180M Maturity', color: 'bg-blue-500/20 text-blue-400' },
            { label: '+', color: 'text-slate-500' },
            { label: '$120M FX Hedge', color: 'bg-purple-500/20 text-purple-400' },
            { label: '+', color: 'text-slate-500' },
            { label: '$65M Coupon', color: 'bg-amber-500/20 text-amber-400' },
            { label: '+', color: 'text-slate-500' },
            { label: '$35M Operations', color: 'bg-cyan-500/20 text-cyan-400' },
          ].map((item, i) => (
            <span key={i} className={`px-3 py-1.5 rounded-lg text-sm font-medium ${item.color}`}>
              {item.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
