import { useState } from 'react';
import Card, { CardHeader } from './ui/Card';
import Badge from './ui/Badge';
import Button from './ui/Button';

type CrisisType = 'banking' | 'currency' | 'pandemic' | 'trade' | 'natural';

interface CrisisMode {
  id: CrisisType;
  name: string;
  icon: string;
  description: string;
  priorityMetrics: string[];
  actions: string[];
  status: string;
}

const CRISIS_MODES: CrisisMode[] = [
  {
    id: 'banking', name: 'Banking Crisis', icon: 'Landmark',
    description: 'Systemic banking stress requiring immediate liquidity support and potential recapitalization.',
    priorityMetrics: ['Liquidity Coverage Ratio', 'Bank Capital Adequacy', 'Deposit Flight Risk', 'Interbank Spread', 'Emergency Funding Available'],
    actions: ['Activate emergency liquidity facilities', 'Assess bank capital positions', 'Coordinate with central bank', 'Prepare deposit guarantee communications'],
    status: 'Ready' },
  {
    id: 'currency', name: 'Currency Collapse', icon: '💱',
    description: 'Rapid currency depreciation threatening import costs, debt servicing, and inflation.',
    priorityMetrics: ['FX Reserve Coverage', 'Import Cover (months)', 'Debt/FX Ratio', 'Intervention Capacity', 'Capital Controls Status'],
    actions: ['Assess intervention capacity', 'Activate swap lines', 'Consider capital controls', 'Communicate with IMF'],
    status: 'Ready' },
  {
    id: 'pandemic', name: 'Pandemic', icon: '🦠',
    description: 'Global pandemic requiring fiscal response, health spending, and economic support.',
    priorityMetrics: ['Emergency Fiscal Space', 'Health Spending Capacity', 'GDP Impact Estimate', 'Social Safety Net Coverage', 'Debt Sustainability'],
    actions: ['Estimate fiscal cost', 'Assess emergency spending capacity', 'Model GDP impact', 'Coordinate international response'],
    status: 'Ready' },
  {
    id: 'trade', name: 'Trade Embargo', icon: '🚢',
    description: 'Trade restrictions or sanctions disrupting export revenue and supply chains.',
    priorityMetrics: ['Export Revenue at Risk', 'Import Substitution Capacity', 'FX Revenue Impact', 'Sanctions Exposure', 'Supply Chain Resilience'],
    actions: ['Map sanctions exposure', 'Identify alternative markets', 'Assess import substitution', 'Prepare trade finance facilities'],
    status: 'Ready' },
  {
    id: 'natural', name: 'Natural Disaster', icon: '🌪️',
    description: 'Major natural disaster requiring reconstruction funding and emergency budget reallocation.',
    priorityMetrics: ['Emergency Fund Balance', 'Insurance Coverage', 'Reconstruction Cost Estimate', 'Budget Flexibility', 'International Aid Potential'],
    actions: ['Activate emergency funds', 'Assess reconstruction cost', 'Coordinate international aid', 'Prepare supplementary budget'],
    status: 'Ready' },
];

export default function WarRoom() {
  const [activeMode, setActiveMode] = useState<CrisisType | null>(null);
  const [activating, setActivating] = useState(false);

  const activateMode = async (mode: CrisisType) => {
    setActivating(true);
    setActiveMode(mode);
    await new Promise((r) => setTimeout(r, 800));
    setActivating(false);
  };

  const active = CRISIS_MODES.find((m) => m.id === activeMode);

  return (
    <div className="space-y-6">
      {/* War room header */}
      <div className={`rounded-2xl p-6 ${activeMode ? 'bg-gradient-to-br from-red-900 via-red-800 to-slate-900 text-white' : 'bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white'}`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-red-400 mb-1">
              {activeMode ? '🔴 CRISIS MODE ACTIVE' : '⚪ STANDBY'}
            </p>
            <h2 className="text-xl font-bold">{active ? active.name : 'Quantive War Room'}</h2>
            <p className="text-sm text-slate-300 mt-1">{active ? active.description : 'Select a crisis scenario to activate focused monitoring and response tools.'}</p>
          </div>
          {activeMode && (
            <Button variant="danger" size="sm" onClick={() => setActiveMode(null)}>Deactivate</Button>
          )}
        </div>
      </div>

      {/* Crisis mode selection */}
      {!activeMode && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {CRISIS_MODES.map((mode) => (
            <button
              key={mode.id}
              onClick={() => activateMode(mode.id)}
              disabled={activating}
              className="text-left bg-white/60 backdrop-blur-xl border border-white/60 rounded-2xl p-5 hover:shadow-lg hover:bg-white/80 transition-all"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-2xl">{mode.icon}</span>
                <Badge variant="success">{mode.status}</Badge>
              </div>
              <h3 className="text-sm font-bold text-slate-900">{mode.name}</h3>
              <p className="text-xs text-slate-500 mt-1 line-clamp-2">{mode.description}</p>
            </button>
          ))}
        </div>
      )}

      {/* Active crisis dashboard */}
      {activeMode && active && (
        <div className="space-y-4">
          {/* Priority metrics grid */}
          <Card>
            <CardHeader title="Priority Metrics" subtitle="Real-time monitoring for this crisis scenario" />
            <div className="px-6 pb-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {active.priorityMetrics.map((metric, i) => (
                <div key={i} className="bg-white/50 backdrop-blur rounded-xl p-4 border border-white/40">
                  <p className="text-[10px] uppercase tracking-wider text-slate-400 mb-1">{metric}</p>
                  <div className="flex items-end gap-2">
                    <p className="text-xl font-bold text-slate-900 tabular-nums">
                      {['87%', '$45B', '3.2x', '120bps', '$18B', '42%', '65%', '2.1%', '$12B', '72%'][i % 10]}
                    </p>
                    <Badge variant={i % 3 === 0 ? 'danger' : i % 3 === 1 ? 'warning' : 'success'}>
                      {i % 3 === 0 ? 'Critical' : i % 3 === 1 ? 'Watch' : 'OK'}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Response actions */}
          <Card>
            <CardHeader title="Response Actions" subtitle="Pre-planned actions for this crisis scenario" />
            <div className="px-6 pb-6 space-y-3">
              {active.actions.map((action, i) => (
                <div key={i} className="flex items-center gap-3 p-3 bg-white/50 backdrop-blur rounded-xl border border-white/40">
                  <span className="flex items-center justify-center w-7 h-7 rounded-full bg-slate-100 text-xs font-bold text-slate-600">{i + 1}</span>
                  <p className="text-sm text-slate-700 flex-1">{action}</p>
                  <Button variant="ghost" size="sm">Execute</Button>
                </div>
              ))}
            </div>
          </Card>

          {/* Live indicators */}
          <Card>
            <CardHeader title="Live Indicators" subtitle="Bloomberg Terminal-style overview" />
            <div className="px-6 pb-6 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
              {[
                { label: '10Y Yield', value: '4.65%', color: 'text-slate-900' },
                { label: '2s10s', value: '+33bp', color: 'text-emerald-600' },
                { label: 'CDS 5Y', value: '145bp', color: 'text-red-600' },
                { label: 'FX Spot', value: '1.0845', color: 'text-slate-900' },
                { label: 'VIX', value: '14.2', color: 'text-emerald-600' },
                { label: 'Reserves', value: '$450B', color: 'text-blue-600' },
              ].map((m) => (
                <div key={m.label} className="bg-slate-900 text-white rounded-xl p-3 text-center">
                  <p className="text-[10px] text-slate-400 uppercase">{m.label}</p>
                  <p className={`text-lg font-bold tabular-nums ${m.color === 'text-emerald-600' ? 'text-emerald-400' : m.color === 'text-red-600' ? 'text-red-400' : m.color === 'text-blue-600' ? 'text-blue-400' : 'text-white'}`}>{m.value}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
