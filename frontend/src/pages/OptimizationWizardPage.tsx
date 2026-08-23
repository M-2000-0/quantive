import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import AppShell from '../components/layout/AppShell';
import { Button, Card, CardHeader, Badge } from '../components/ui';
import { api } from '../api';
import { MOCK_PORTFOLIOS } from '../api/mock';
import type { Portfolio, OptimizationJob } from '../types';

type WizardStep = 'portfolio' | 'objectives' | 'constraints' | 'scenarios' | 'review' | 'run';

const STEP_CONFIG: { key: WizardStep; label: string; num: number }[] = [
  { key: 'portfolio', label: 'Portfolio', num: 1 },
  { key: 'objectives', label: 'Objectives', num: 2 },
  { key: 'constraints', label: 'Constraints', num: 3 },
  { key: 'scenarios', label: 'Scenarios', num: 4 },
  { key: 'review', label: 'Review', num: 5 },
  { key: 'run', label: 'Run', num: 6 },
];

const NAMED_SCENARIOS = [
  { id: 'base', label: 'Base', desc: 'Current market conditions baseline', always: true },
  { id: 'high_interest', label: 'High Interest Rates', desc: '200bps rate increase across all maturities' },
  { id: 'low_interest', label: 'Low Interest Rates', desc: '100bps rate decrease across all maturities' },
  { id: 'high_inflation', label: 'High Inflation', desc: 'Inflation surge with real rate compression' },
  { id: 'fx_shock', label: 'FX Shock', desc: 'Major currency depreciation event (15-25%)' },
  { id: 'liquidity_shock', label: 'Liquidity Shock', desc: 'Severe market liquidity contraction' },
];

const OPTIMIZATION_STEPS = [
  { id: 'formulate', label: 'FORMULATING PROBLEM' },
  { id: 'scenarios', label: 'GENERATING SCENARIOS' },
  { id: 'classical', label: 'CLASSICAL OPTIMIZATION' },
  { id: 'heuristic', label: 'HEURISTIC OPTIMIZATION' },
  { id: 'quantum', label: 'QUANTUM-INSPIRED' },
  { id: 'benchmarking', label: 'BENCHMARKING' },
  { id: 'stress', label: 'STRESS TESTING' },
];

interface WizardState {
  portfolioId: string;
  portfolio: Portfolio | null;
  optimizationName: string;
  objectives: { financing: number; refinancing: number; interestRate: number; currency: number };
  constraints: {
    maxFinancingCost: { enabled: boolean; value: string };
    maxRefinancingConcentration: { enabled: boolean; value: string };
    maxCurrencyExposure: { enabled: boolean; value: string };
    maxFloatingRateExposure: { enabled: boolean; value: string };
    minLiquidity: { enabled: boolean; value: string };
    maturityConcentrationLimit: { enabled: boolean; value: string };
  };
  selectedScenarios: string[];
  monteCarloCount: number;
  monteCarloSeed: number;
  includeBaseInMc: boolean;
  solverSeed: number;
}

const defaultState: WizardState = {
  portfolioId: '',
  portfolio: null,
  optimizationName: 'Debt Portfolio Optimization',
  objectives: { financing: 35, refinancing: 25, interestRate: 20, currency: 20 },
  constraints: {
    maxFinancingCost: { enabled: false, value: '' },
    maxRefinancingConcentration: { enabled: true, value: '0.30' },
    maxCurrencyExposure: { enabled: false, value: '' },
    maxFloatingRateExposure: { enabled: true, value: '0.25' },
    minLiquidity: { enabled: true, value: '5000000000' },
    maturityConcentrationLimit: { enabled: true, value: '0.35' },
  },
  selectedScenarios: ['base'],
  monteCarloCount: 10000,
  monteCarloSeed: 42,
  includeBaseInMc: true,
  solverSeed: 42,
};

function normalizeObjectives(obj: WizardState['objectives']) {
  const total = obj.financing + obj.refinancing + obj.interestRate + obj.currency;
  if (total === 0) return { financing: 25, refinancing: 25, interestRate: 25, currency: 25 };
  return {
    financing: Math.round((obj.financing / total) * 100),
    refinancing: Math.round((obj.refinancing / total) * 100),
    interestRate: Math.round((obj.interestRate / total) * 100),
    currency: 100 - Math.round((obj.financing / total) * 100) - Math.round((obj.refinancing / total) * 100) - Math.round((obj.interestRate / total) * 100),
  };
}

function formatCurrency(v: number): string {
  if (v >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
  if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(2)}M`;
  return `$${v.toLocaleString()}`;
}

export default function OptimizationWizardPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [step, setStep] = useState<WizardStep>('portfolio');
  const [state, setState] = useState<WizardState>(() => ({
    ...defaultState,
    portfolioId: searchParams.get('portfolio') || '',
  }));
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [, setLoadingPortfolios] = useState(true);
  const [, setRunning] = useState(false);
  const [runError, setRunError] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobProgress, setJobProgress] = useState<OptimizationJob | null>(null);
  const [completedSteps, setCompletedSteps] = useState<Record<string, 'completed' | 'running' | 'pending'>>({});
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const preselectId = searchParams.get('portfolio') || '';

  useEffect(() => {
    setLoadingPortfolios(true);
    api.portfolios.list()
      .then((res) => {
        setPortfolios(res.portfolios);
        if (preselectId) {
          const p = res.portfolios.find((x) => x.id === preselectId);
          if (p) setState((s) => ({ ...s, portfolio: p }));
        }
      })
      .catch(() => setPortfolios(MOCK_PORTFOLIOS))
      .finally(() => setLoadingPortfolios(false));
  }, [preselectId]);

  const selectPortfolio = (id: string) => {
    const p = portfolios.find((x) => x.id === id) || null;
    setState((s) => ({ ...s, portfolioId: id, portfolio: p }));
  };

  const norms = normalizeObjectives(state.objectives);

  const canAdvance = useCallback((): boolean => {
    switch (step) {
      case 'portfolio': return !!state.portfolioId;
      case 'objectives': return true;
      case 'constraints': return true;
      case 'scenarios': return state.selectedScenarios.length > 0;
      case 'review': return true;
      default: return true;
    }
  }, [step, state]);

  const stepIndex = STEP_CONFIG.findIndex((s) => s.key === step);

  const goNext = () => {
    if (!canAdvance()) return;
    const next = STEP_CONFIG[stepIndex + 1];
    if (next) setStep(next.key);
  };

  const goBack = () => {
    const prev = STEP_CONFIG[stepIndex - 1];
    if (prev) setStep(prev.key);
  };

  const runOptimization = async () => {
    setRunning(true);
    setRunError('');
    setStep('run');

    const buildConstraints = (): Record<string, unknown> => {
      const c: Record<string, unknown> = {};
      const s = state.constraints;
      if (s.maxFinancingCost.enabled && s.maxFinancingCost.value) c.max_financing_cost = parseFloat(s.maxFinancingCost.value);
      if (s.maxRefinancingConcentration.enabled && s.maxRefinancingConcentration.value) c.max_refinancing_concentration = parseFloat(s.maxRefinancingConcentration.value);
      if (s.maxCurrencyExposure.enabled && s.maxCurrencyExposure.value) c.max_currency_exposure = parseFloat(s.maxCurrencyExposure.value);
      if (s.maxFloatingRateExposure.enabled && s.maxFloatingRateExposure.value) c.max_floating_rate_exposure = parseFloat(s.maxFloatingRateExposure.value);
      if (s.minLiquidity.enabled && s.minLiquidity.value) c.min_liquidity = parseFloat(s.minLiquidity.value);
      if (s.maturityConcentrationLimit.enabled && s.maturityConcentrationLimit.value) c.maturity_concentration_limit = parseFloat(s.maturityConcentrationLimit.value);
      return c;
    };

    try {
      const job = await api.optimizations.create({
        portfolio_id: state.portfolioId,
        name: state.optimizationName,
        optimization_type: 'multi_objective',
        objectives: {
          financing_cost_weight: norms.financing / 100,
          refinancing_risk_weight: norms.refinancing / 100,
          interest_rate_risk_weight: norms.interestRate / 100,
          currency_risk_weight: norms.currency / 100,
        },
        constraints: buildConstraints(),
        solver_config: {
          solvers: ['classical', 'heuristic', 'quantum_inspired'],
          time_limit_seconds: 120,
          seed: state.solverSeed,
        },
        scenario_config: {
          include_named: state.selectedScenarios,
          monte_carlo_count: state.monteCarloCount,
          monte_carlo_seed: state.monteCarloSeed,
          include_base_in_mc: state.includeBaseInMc,
        },
        random_seed: state.solverSeed,
      });
      setJobId(job.id);
      startPolling(job.id);
    } catch (e: unknown) {
      setRunError(e instanceof Error ? e.message : 'Failed to start optimization');
      setRunning(false);
    }
  };

  const startPolling = (id: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    const startTime = Date.now();

    pollRef.current = setInterval(async () => {
      try {
        const job = await api.optimizations.get(id);
        setJobProgress(job);

        const progress = job.progress;
        const stepsDone = Math.floor(progress * OPTIMIZATION_STEPS.length);
        const newCompleted: Record<string, 'completed' | 'running' | 'pending'> = {};
        OPTIMIZATION_STEPS.forEach((s, i) => {
          if (i < stepsDone) newCompleted[s.id] = 'completed';
          else if (i === stepsDone && progress < 1) newCompleted[s.id] = 'running';
          else newCompleted[s.id] = 'pending';
        });
        setCompletedSteps(newCompleted);

        if (job.status === 'completed' || job.status === 'failed') {
          if (pollRef.current) clearInterval(pollRef.current);
          setRunning(false);
          if (job.status === 'completed') {
            OPTIMIZATION_STEPS.forEach((s) => setCompletedSteps((prev) => ({ ...prev, [s.id]: 'completed' })));
          }
        }
      } catch {
        if (Date.now() - startTime > 5000) {
          if (pollRef.current) clearInterval(pollRef.current);
          setRunning(false);
          setRunError('Lost connection to optimization engine');
        }
      }
    }, 1500);
  };

  useEffect(() => { return () => { if (pollRef.current) clearInterval(pollRef.current); }; }, []);

  const StepHeader = () => (
    <div className="flex items-center gap-2 mb-8 overflow-x-auto pb-2">
      {STEP_CONFIG.map((s, i) => {
        const isComplete = i < stepIndex;
        const isCurrent = s.key === step;
        return (
          <div key={s.key} className="flex items-center gap-2 flex-shrink-0">
            {i > 0 && <div className={`w-6 h-px ${isComplete ? 'bg-blue-600' : 'bg-slate-200'}`} />}
            <div className="flex items-center gap-2">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${isComplete ? 'bg-blue-600 text-white' : isCurrent ? 'bg-blue-600 text-white ring-2 ring-blue-200' : 'bg-slate-200 text-slate-500'}`}>
                {isComplete ? (
                  <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                ) : s.num}
              </div>
              <span className={`text-xs font-medium whitespace-nowrap ${isCurrent ? 'text-slate-900' : isComplete ? 'text-blue-600' : 'text-slate-400'}`}>{s.label}</span>
            </div>
          </div>
        );
      })}
    </div>
  );

  const ConstraintToggle = ({ label, constraintKey, placeholder }: { label: string; constraintKey: keyof WizardState['constraints']; placeholder?: string }) => {
    const c = state.constraints[constraintKey];
    return (
      <div className="flex items-center gap-4 p-3 rounded-lg border border-slate-200 hover:border-slate-300 transition-colors">
        <button
          onClick={() => setState((s) => ({ ...s, constraints: { ...s.constraints, [constraintKey]: { ...s.constraints[constraintKey], enabled: !s.constraints[constraintKey].enabled } } }))}
          className={`relative w-10 h-5 rounded-full transition-colors flex-shrink-0 ${c.enabled ? 'bg-blue-600' : 'bg-slate-300'}`}
        >
          <span className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${c.enabled ? 'translate-x-5' : ''}`} />
        </button>
        <span className="text-sm font-medium text-slate-700 min-w-[200px]">{label}</span>
        <input
          type="text"
          value={c.value}
          onChange={(e) => setState((s) => ({ ...s, constraints: { ...s.constraints, [constraintKey]: { ...s.constraints[constraintKey], value: e.target.value } } }))}
          disabled={!c.enabled}
          placeholder={placeholder || 'Value'}
          className="flex-1 px-3 py-1.5 border border-slate-200 rounded-md text-sm text-slate-900 placeholder:text-slate-400 disabled:opacity-40 disabled:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>
    );
  };

  return (
    <AppShell>
      <div className="px-8 py-6 max-w-5xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Optimization Wizard</h1>
          <p className="mt-1 text-sm text-slate-500">Configure and run a multi-objective debt optimization</p>
        </div>

        <StepHeader />

        {runError && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">{runError}</div>
        )}

        {/* Step 1: Portfolio Selection */}
        {step === 'portfolio' && (
          <div className="space-y-6">
            <Card>
              <CardHeader title="Select Portfolio" subtitle="Choose the debt portfolio to optimize" />
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Portfolio</label>
                  <select
                    value={state.portfolioId}
                    onChange={(e) => selectPortfolio(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">Select a portfolio</option>
                    {portfolios.map((p) => (
                      <option key={p.id} value={p.id}>{p.name} ({p.instruments.length} instruments)</option>
                    ))}
                  </select>
                </div>

                {state.portfolio && (
                  <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                    <div className="flex items-start gap-4">
                      <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0">
                        <svg className="h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                        </svg>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-slate-900">{state.portfolio.name}</p>
                        <p className="text-xs text-slate-500 mt-0.5">{state.portfolio.description}</p>
                        <div className="flex items-center gap-4 mt-2">
                          <span className="text-xs text-slate-500"><strong className="text-slate-700">{state.portfolio.instruments.length}</strong> instruments</span>
                          <span className="text-xs text-slate-500"><strong className="text-slate-700">{formatCurrency(state.portfolio.instruments.reduce((s, i) => s + i.principal_outstanding, 0))}</strong> total principal</span>
                          <span className="text-xs text-slate-500"><strong className="text-slate-700">{Array.from(new Set(state.portfolio.instruments.map((i) => i.currency))).length}</strong> currencies</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Optimization Name</label>
                  <input type="text" value={state.optimizationName} onChange={(e) => setState((s) => ({ ...s, optimizationName: e.target.value }))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                </div>

                <button onClick={() => navigate('/portfolios/new')} className="text-sm text-blue-600 hover:text-blue-800 font-medium">
                  + Create new portfolio
                </button>
              </div>
            </Card>
          </div>
        )}

        {/* Step 2: Objectives */}
        {step === 'objectives' && (
          <div className="space-y-6">
            <Card>
              <CardHeader title="Optimization Objectives" subtitle="Set the relative importance of each objective (auto-normalized to 100%)" />
              <div className="space-y-6">
                {([
                  ['financing', 'Financing Cost', 'Minimize total debt service cost'],
                  ['refinancing', 'Refinancing Risk', 'Reduce rollover and refinancing concentration'],
                  ['interestRate', 'Interest Rate Risk', 'Minimize exposure to rate volatility'],
                  ['currency', 'Currency Risk', 'Reduce foreign exchange exposure'],
                ] as const).map(([key, label, desc]) => (
                  <div key={key}>
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <span className="text-sm font-semibold text-slate-900">{label}</span>
                        <span className="text-xs text-slate-400 ml-2">{desc}</span>
                      </div>
                      <span className="text-sm font-bold text-blue-600">{norms[key]}%</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-slate-400 w-6 text-right">0</span>
                      <input type="range" min={0} max={100} value={state.objectives[key]}
                        onChange={(e) => setState((s) => ({ ...s, objectives: { ...s.objectives, [key]: parseInt(e.target.value) } }))}
                        className="flex-1 h-2 bg-slate-200 rounded-full appearance-none cursor-pointer accent-blue-600" />
                      <span className="text-xs text-slate-400 w-6">100</span>
                    </div>
                  </div>
                ))}

                <div className="pt-4 border-t border-slate-200">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Relative Weight Distribution</p>
                  <div className="h-8 rounded-lg overflow-hidden flex">
                    <div className="bg-blue-600 flex items-center justify-center text-white text-xs font-bold transition-all" style={{ width: `${norms.financing}%` }}>
                      {norms.financing > 8 ? `${norms.financing}%` : ''}
                    </div>
                    <div className="bg-blue-500 flex items-center justify-center text-white text-xs font-bold transition-all" style={{ width: `${norms.refinancing}%` }}>
                      {norms.refinancing > 8 ? `${norms.refinancing}%` : ''}
                    </div>
                    <div className="bg-blue-400 flex items-center justify-center text-white text-xs font-bold transition-all" style={{ width: `${norms.interestRate}%` }}>
                      {norms.interestRate > 8 ? `${norms.interestRate}%` : ''}
                    </div>
                    <div className="bg-blue-300 flex items-center justify-center text-slate-700 text-xs font-bold transition-all" style={{ width: `${norms.currency}%` }}>
                      {norms.currency > 8 ? `${norms.currency}%` : ''}
                    </div>
                  </div>
                  <div className="flex mt-2 text-xs text-slate-500">
                    <span className="flex-1 text-center">Cost</span>
                    <span className="flex-1 text-center">Refinancing</span>
                    <span className="flex-1 text-center">Rate</span>
                    <span className="flex-1 text-center">Currency</span>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Step 3: Constraints */}
        {step === 'constraints' && (
          <div className="space-y-6">
            <Card>
              <CardHeader title="Portfolio Constraints" subtitle="Enable and configure constraints to limit optimization search space" />
              <div className="space-y-3">
                <ConstraintToggle label="Max Financing Cost ($)" constraintKey="maxFinancingCost" placeholder="e.g. 7000000000" />
                <ConstraintToggle label="Max Refinancing Concentration" constraintKey="maxRefinancingConcentration" placeholder="0.0 - 1.0" />
                <ConstraintToggle label="Max Currency Exposure" constraintKey="maxCurrencyExposure" placeholder="0.0 - 1.0" />
                <ConstraintToggle label="Max Floating-Rate Exposure" constraintKey="maxFloatingRateExposure" placeholder="0.0 - 1.0" />
                <ConstraintToggle label="Minimum Liquidity ($)" constraintKey="minLiquidity" placeholder="e.g. 5000000000" />
                <ConstraintToggle label="Maturity Concentration Limit" constraintKey="maturityConcentrationLimit" placeholder="0.0 - 1.0" />
              </div>
            </Card>
          </div>
        )}

        {/* Step 4: Scenarios */}
        {step === 'scenarios' && (
          <div className="space-y-6">
            <Card>
              <CardHeader title="Named Scenarios" subtitle="Select stress scenarios to include in the analysis" />
              <div className="grid grid-cols-2 gap-3">
                {NAMED_SCENARIOS.map((sc) => {
                  const selected = state.selectedScenarios.includes(sc.id);
                  return (
                    <button key={sc.id} disabled={sc.always}
                      onClick={() => {
                        if (sc.always) return;
                        setState((s) => ({
                          ...s,
                          selectedScenarios: selected ? s.selectedScenarios.filter((x) => x !== sc.id) : [...s.selectedScenarios, sc.id],
                        }));
                      }}
                      className={`p-3 rounded-lg border text-left transition-all ${selected ? 'border-blue-400 bg-blue-50/50 ring-1 ring-blue-200' : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'} ${sc.always ? 'opacity-80' : 'cursor-pointer'}`}>
                      <div className="flex items-center gap-2">
                        <div className={`w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 ${selected ? 'border-blue-600 bg-blue-600' : 'border-slate-300'}`}>
                          {selected && <svg className="h-2.5 w-2.5 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-slate-900">{sc.label}</p>
                          <p className="text-xs text-slate-500">{sc.desc}</p>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </Card>

            <Card>
              <CardHeader title="Monte Carlo Settings" subtitle="Configure random scenario generation" />
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm font-medium text-slate-700">Number of Scenarios</label>
                    <span className="text-sm font-bold text-slate-900">{state.monteCarloCount.toLocaleString()}</span>
                  </div>
                  <input type="range" min={100} max={50000} step={100} value={state.monteCarloCount}
                    onChange={(e) => setState((s) => ({ ...s, monteCarloCount: parseInt(e.target.value) }))}
                    className="w-full h-2 bg-slate-200 rounded-full appearance-none cursor-pointer accent-blue-600" />
                  <div className="flex justify-between text-xs text-slate-400 mt-1"><span>100</span><span>50,000</span></div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">Random Seed</label>
                    <input type="number" value={state.monteCarloSeed}
                      onChange={(e) => setState((s) => ({ ...s, monteCarloSeed: parseInt(e.target.value) || 0 }))}
                      className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">Solver Seed</label>
                    <input type="number" value={state.solverSeed}
                      onChange={(e) => setState((s) => ({ ...s, solverSeed: parseInt(e.target.value) || 0 }))}
                      className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                  <button onClick={() => setState((s) => ({ ...s, includeBaseInMc: !s.includeBaseInMc }))}
                    className={`relative w-10 h-5 rounded-full transition-colors flex-shrink-0 ${state.includeBaseInMc ? 'bg-blue-600' : 'bg-slate-300'}`}>
                    <span className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${state.includeBaseInMc ? 'translate-x-5' : ''}`} />
                  </button>
                  <span className="text-sm text-slate-700">Include base scenario in Monte Carlo set</span>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Step 5: Review */}
        {step === 'review' && (
          <div className="space-y-6">
            <Card>
              <CardHeader title="Configuration Summary" subtitle="Review all settings before running optimization" />
              <div className="space-y-5">
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Portfolio</p>
                    <div className="p-3 bg-slate-50 rounded-lg">
                      <p className="text-sm font-semibold text-slate-900">{state.portfolio?.name || 'Not selected'}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{state.portfolio?.instruments.length || 0} instruments &middot; {formatCurrency(state.portfolio?.instruments.reduce((s, i) => s + i.principal_outstanding, 0) || 0)}</p>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Optimization Name</p>
                    <div className="p-3 bg-slate-50 rounded-lg">
                      <p className="text-sm font-semibold text-slate-900">{state.optimizationName}</p>
                    </div>
                  </div>
                </div>

                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Objective Weights (Normalized)</p>
                  <div className="h-8 rounded-lg overflow-hidden flex">
                    <div className="bg-blue-600 flex items-center justify-center text-white text-xs font-bold" style={{ width: `${norms.financing}%` }}>{norms.financing > 8 ? `${norms.financing}%` : ''}</div>
                    <div className="bg-blue-500 flex items-center justify-center text-white text-xs font-bold" style={{ width: `${norms.refinancing}%` }}>{norms.refinancing > 8 ? `${norms.refinancing}%` : ''}</div>
                    <div className="bg-blue-400 flex items-center justify-center text-white text-xs font-bold" style={{ width: `${norms.interestRate}%` }}>{norms.interestRate > 8 ? `${norms.interestRate}%` : ''}</div>
                    <div className="bg-blue-300 flex items-center justify-center text-slate-700 text-xs font-bold" style={{ width: `${norms.currency}%` }}>{norms.currency > 8 ? `${norms.currency}%` : ''}</div>
                  </div>
                  <div className="flex mt-1 text-xs text-slate-500">
                    <span className="flex-1 text-center">Cost {norms.financing}%</span>
                    <span className="flex-1 text-center">Refinancing {norms.refinancing}%</span>
                    <span className="flex-1 text-center">Rate {norms.interestRate}%</span>
                    <span className="flex-1 text-center">Currency {norms.currency}%</span>
                  </div>
                </div>

                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Enabled Constraints</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(state.constraints).filter(([, v]) => v.enabled).map(([key, v]) => (
                      <Badge key={key} variant="outline" size="md">
                        {key.replace(/([A-Z])/g, ' $1').replace(/^./, (s) => s.toUpperCase())}: {v.value}
                      </Badge>
                    ))}
                    {Object.values(state.constraints).every((v) => !v.enabled) && (
                      <span className="text-sm text-slate-400">No constraints enabled</span>
                    )}
                  </div>
                </div>

                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Scenarios</p>
                  <div className="flex flex-wrap gap-2">
                    {state.selectedScenarios.map((scId) => {
                      const sc = NAMED_SCENARIOS.find((s) => s.id === scId);
                      return <Badge key={scId} variant="info" size="md">{sc?.label || scId}</Badge>;
                    })}
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4 p-4 bg-slate-50 rounded-lg">
                  <div>
                    <p className="text-xs text-slate-500">Monte Carlo Scenarios</p>
                    <p className="text-sm font-bold text-slate-900">{state.monteCarloCount.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Total Scenario Count</p>
                    <p className="text-sm font-bold text-slate-900">{(state.selectedScenarios.length + state.monteCarloCount).toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Solvers</p>
                    <p className="text-sm font-bold text-slate-900">Classical + Heuristic + Quantum-Inspired</p>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Step 6: Run & Progress */}
        {step === 'run' && (
          <div className="space-y-6">
            <Card>
              {!jobId ? (
                <div className="text-center py-12">
                  <p className="text-sm text-slate-500 mb-4">Ready to begin optimization</p>
                  <Button variant="primary" size="lg" onClick={runOptimization}>
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
                    </svg>
                    Start Optimization
                  </Button>
                </div>
              ) : (
                <div className="py-6">
                  <div className="text-center mb-8">
                    <h2 className="text-lg font-bold text-slate-900 tracking-tight uppercase">Optimization In Progress</h2>
                    <div className="w-32 h-px bg-slate-200 mx-auto mt-3" />
                  </div>

                  <div className="max-w-lg mx-auto space-y-2">
                    {OPTIMIZATION_STEPS.map((s) => {
                      const status = completedSteps[s.id] || 'pending';
                      return (
                        <div key={s.id} className="flex items-center gap-3 py-2">
                          <div className="w-5 h-5 flex-shrink-0 flex items-center justify-center">
                            {status === 'completed' && (
                              <div className="w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center">
                                <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                                </svg>
                              </div>
                            )}
                            {status === 'running' && (
                              <div className="w-5 h-5 rounded-full bg-blue-600 flex items-center justify-center animate-pulse">
                                <div className="w-2 h-2 rounded-full bg-white" />
                              </div>
                            )}
                            {status === 'pending' && (
                              <div className="w-5 h-5 rounded-full border-2 border-slate-300" />
                            )}
                          </div>
                          <span className={`text-sm font-mono ${status === 'completed' ? 'text-emerald-600' : status === 'running' ? 'text-blue-600 font-semibold' : 'text-slate-400'}`}>
                            {s.label}
                          </span>
                          <span className={`ml-auto text-xs font-mono ${status === 'completed' ? 'text-emerald-600' : status === 'running' ? 'text-blue-600' : 'text-slate-400'}`}>
                            {status === 'completed' ? 'Complete' : status === 'running' ? 'Running...' : 'Pending'}
                          </span>
                        </div>
                      );
                    })}
                  </div>

                  <div className="max-w-lg mx-auto mt-6">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-slate-700">Overall</span>
                      <span className="text-sm font-bold text-slate-900">{Math.round((jobProgress?.progress || 0) * 100)}% complete</span>
                    </div>
                    <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-3 bg-blue-600 rounded-full transition-all duration-700 ease-out" style={{ width: `${(jobProgress?.progress || 0) * 100}%` }} />
                    </div>
                  </div>

                  {jobProgress?.status === 'completed' && (
                    <div className="text-center mt-8">
                      <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-3">
                        <svg className="h-6 w-6 text-emerald-600" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                        </svg>
                      </div>
                      <p className="text-sm font-semibold text-emerald-700">Optimization completed successfully</p>
                      <Button variant="primary" className="mt-4" onClick={() => navigate(`/optimizations/${jobId}`)}>
                        View Results
                      </Button>
                    </div>
                  )}

                  {jobProgress?.status === 'failed' && (
                    <div className="text-center mt-8">
                      <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-3">
                        <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </div>
                      <p className="text-sm font-semibold text-red-700">{jobProgress.error_message || 'Optimization failed'}</p>
                    </div>
                  )}
                </div>
              )}
            </Card>
          </div>
        )}

        {/* Navigation */}
        {step !== 'run' && (
          <div className="flex items-center justify-between mt-8 pt-6 border-t border-slate-200">
            <Button variant="ghost" onClick={goBack} disabled={stepIndex === 0}>
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
              </svg>
              Back
            </Button>
            {step === 'review' ? (
              <Button variant="primary" onClick={runOptimization}>
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
                </svg>
                Run Optimization
              </Button>
            ) : (
              <Button variant="primary" onClick={goNext} disabled={!canAdvance()}>
                Next
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </Button>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
