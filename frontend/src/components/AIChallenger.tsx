import { useState } from 'react';
import Card, { CardHeader } from './ui/Card';
import Badge from './ui/Badge';

interface AIViewpoint {
  id: string;
  name: string;
  persona: string;
  stance: 'bullish' | 'bearish' | 'neutral' | 'contrarian';
  recommendation: string;
  reasoning: string[];
  counterarguments: string[];
  confidence: number;
  risks: string[];
}

const VIEWPOINTS: AIViewpoint[] = [
  {
    id: 'ai1', name: 'Strategic Optimizer', persona: 'Cost-minimizing solver',
    stance: 'neutral', recommendation: 'Issue 20-year bonds at current rates to lock in long-term financing and reduce refinancing wall.',
    reasoning: [
      'Current 10Y yield at 4.65% is below 10-year average of 5.2%',
      'Long-dated issuance reduces refinancing concentration risk',
      'Oversubscription rates suggest strong investor demand for long-end paper',
    ],
    counterarguments: ['If rates fall further, we lock in above-market cost', 'Reduces optionality for future portfolio management'],
    confidence: 82, risks: ['Rate volatility', 'Duration extension risk'] },
  {
    id: 'ai2', name: 'Risk Sentinel', persona: 'Conservative risk manager',
    stance: 'bearish', recommendation: 'Wait for clarity on Fed policy direction. Current issuance could lock in rates before a potential 100bps decline.',
    reasoning: [
      'Fed dot plot suggests rate cuts in 2027',
      'Historical pattern: 65% of time, rates fall within 12 months of peak',
      'Premature long-dated issuance has cost governments $2-5B in suboptimal pricing',
    ],
    counterarguments: ['Waiting exposes us to refinancing risk if rates rise', 'Investor demand may not persist'],
    confidence: 71, risks: ['Market timing risk', 'Refinancing cliff'] },
  {
    id: 'ai3', name: 'Alternative Strategist', persona: 'Innovation-focused optimizer',
    stance: 'contrarian', recommendation: 'Split issuance: 40% 10Y, 30% green bonds, 30% sustainability-linked bonds to diversify investor base.',
    reasoning: [
      'Green bond framework unlocked $12B in ESG-dedicated demand',
      'Sustainability-linked bonds align with COP commitments',
      'Diversification across bond types reduces single-investor concentration',
    ],
    counterarguments: ['Higher issuance costs (verification, reporting)', 'ESG market sentiment could shift', 'Complexity increases operational burden'],
    confidence: 68, risks: ['ESG market volatility', 'Operational complexity', 'Greenwashing risk'] },
];

const STANCE_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  bullish: { label: 'Bullish', color: 'text-emerald-700', bg: 'bg-emerald-500/12 border-emerald-500/20' },
  bearish: { label: 'Bearish', color: 'text-red-700', bg: 'bg-red-500/12 border-red-500/20' },
  neutral: { label: 'Neutral', color: 'text-blue-700', bg: 'bg-blue-500/12 border-blue-500/20' },
  contrarian: { label: 'Contrarian', color: 'text-violet-700', bg: 'bg-violet-500/12 border-violet-500/20' } };

export default function AIChallenger() {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader title="AI Strategy Debate" subtitle="Three competing AI viewpoints challenge each recommendation" />
        <div className="px-6 pb-6">
          <p className="text-sm text-slate-600">
            Each AI agent is assigned a different optimization objective. They debate strategy, challenge assumptions,
            and present competing viewpoints — mimicking how real government advisory committees work.
          </p>
        </div>
      </Card>

      <div className="space-y-4">
        {VIEWPOINTS.map((vp) => {
          const stance = STANCE_CONFIG[vp.stance];
          return (
            <Card key={vp.id} padding={false}>
              <div
                className="px-6 py-5 cursor-pointer hover:bg-white/30 transition-colors"
                onClick={() => setExpanded(expanded === vp.id ? null : vp.id)}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center text-white text-sm font-bold">
                      {vp.name.charAt(0)}
                    </div>
                    <div>
                      <h3 className="text-[15px] font-bold text-slate-900">{vp.name}</h3>
                      <p className="text-xs text-slate-500">{vp.persona}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={vp.confidence >= 80 ? 'success' : vp.confidence >= 65 ? 'warning' : 'danger'}>
                      {vp.confidence}% confidence
                    </Badge>
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold border ${stance.bg} ${stance.color}`}>
                      {stance.label}
                    </span>
                  </div>
                </div>

                <div className="mt-3 bg-slate-50/80 rounded-xl p-4">
                  <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">Recommendation</p>
                  <p className="text-sm text-slate-800 font-medium">{vp.recommendation}</p>
                </div>

                {expanded === vp.id && (
                  <div className="mt-4 pt-4 border-t border-white/40 space-y-4">
                    <div>
                      <p className="text-[10px] font-bold text-slate-400 uppercase mb-2">Reasoning</p>
                      <div className="space-y-1">
                        {vp.reasoning.map((r, i) => (
                          <div key={i} className="flex items-start gap-2 text-xs text-slate-600">
                            <span className="text-emerald-500 mt-0.5">✓</span>{r}
                          </div>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold text-slate-400 uppercase mb-2">Counterarguments</p>
                      <div className="space-y-1">
                        {vp.counterarguments.map((c, i) => (
                          <div key={i} className="flex items-start gap-2 text-xs text-slate-600">
                            <span className="text-red-500 mt-0.5">✗</span>{c}
                          </div>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold text-slate-400 uppercase mb-2">Key Risks</p>
                      <div className="flex gap-2">
                        {vp.risks.map((r, i) => (
                          <span key={i} className="px-2 py-0.5 text-[10px] font-bold bg-red-50 text-red-600 rounded-full">{r}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
