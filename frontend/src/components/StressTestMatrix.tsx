import { Card } from './ui';
import { Badge } from './ui';

interface StressScenario {
  name: string;
  description: string;
  shocks: Record<string, number>;
  impact: number;
  probability: number;
  status: 'pass' | 'warn' | 'fail';
}

interface StressTestMatrixProps {
  scenarios: StressScenario[];
  riskThreshold: number;
}

export default function StressTestMatrix({ scenarios, riskThreshold }: StressTestMatrixProps) {
  const getImpactColor = (impact: number) => {
    if (impact < riskThreshold * 0.5) return 'text-green-400 bg-green-500/10';
    if (impact < riskThreshold) return 'text-yellow-400 bg-yellow-500/10';
    return 'text-red-400 bg-red-500/10';
  };

  const statusBadge = { pass: 'success', warn: 'warning', fail: 'danger' } as const;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white/80">Stress Test Results</h3>
        <Badge variant="info">Threshold: {riskThreshold}%</Badge>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/10 text-left text-xs text-white/50 uppercase tracking-wider">
              <th className="p-3">Scenario</th>
              <th className="p-3">Impact</th>
              <th className="p-3">Probability</th>
              <th className="p-3">Status</th>
              <th className="p-3">Key Shocks</th>
            </tr>
          </thead>
          <tbody>
            {scenarios.map((s) => (
              <tr key={s.name} className="border-b border-white/5 hover:bg-white/[0.02]">
                <td className="p-3">
                  <div>
                    <span className="text-sm font-medium text-white">{s.name}</span>
                    <p className="text-[10px] text-white/40 mt-0.5">{s.description}</p>
                  </div>
                </td>
                <td className="p-3">
                  <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-bold ${getImpactColor(s.impact)}`}>
                    -{s.impact.toFixed(1)}%
                  </span>
                </td>
                <td className="p-3 text-xs text-white/60">{(s.probability * 100).toFixed(0)}%</td>
                <td className="p-3">
                  <Badge variant={statusBadge[s.status]}>{s.status === 'pass' ? 'Pass' : s.status === 'warn' ? 'Warning' : 'Fail'}</Badge>
                </td>
                <td className="p-3">
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(s.shocks).map(([key, val]) => (
                      <span key={key} className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-white/50">
                        {key}: {val > 0 ? '+' : ''}{val}%
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
