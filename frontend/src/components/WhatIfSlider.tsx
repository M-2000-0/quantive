import { useState } from 'react';
import { Card } from './ui';

interface SliderParam {
  id: string;
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
  unit: string;
  description?: string;
}

interface WhatIfSliderProps {
  params: SliderParam[];
  onChange: (id: string, value: number) => void;
  results?: Record<string, { before: number; after: number; unit: string; label: string }>;
}

export default function WhatIfSlider({ params, onChange, results }: WhatIfSliderProps) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {params.map((p) => (
          <Card key={p.id} className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-white">{p.label}</span>
              <span className="text-sm font-bold text-blue-400">{p.value}{p.unit}</span>
            </div>
            <input
              type="range"
              min={p.min}
              max={p.max}
              step={p.step}
              value={p.value}
              onChange={(e) => onChange(p.id, parseFloat(e.target.value))}
              className="w-full h-2 rounded-full appearance-none cursor-pointer accent-blue-500"
              style={{ background: "rgba(59,130,246,0.2)" }}
            />
            <div className="flex justify-between mt-1">
              <span className="text-[10px] text-white/30">{p.min}{p.unit}</span>
              <span className="text-[10px] text-white/30">{p.max}{p.unit}</span>
            </div>
            {p.description && <p className="text-[10px] text-white/40 mt-1">{p.description}</p>}
          </Card>
        ))}
      </div>

      {results && (
        <Card className="p-4">
          <h4 className="text-sm font-semibold text-white/80 mb-3">Projected Impact</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(results).map(([key, r]) => {
              const change = r.after - r.before;
              const pctChange = r.before !== 0 ? (change / r.before) * 100 : 0;
              const isPositive = key.includes('cost') ? change < 0 : change > 0;
              return (
                <div key={key} className="p-3 rounded-xl bg-white/[0.03] border border-white/5">
                  <p className="text-[10px] text-white/40 mb-1">{r.label}</p>
                  <p className="text-lg font-bold text-white">{r.after.toFixed(1)}{r.unit}</p>
                  <p className={`text-xs font-medium ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                    {change >= 0 ? '+' : ''}{change.toFixed(1)}{r.unit} ({pctChange >= 0 ? '+' : ''}{pctChange.toFixed(1)}%)
                  </p>
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}
