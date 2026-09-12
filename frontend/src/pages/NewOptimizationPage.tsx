import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Check, Loader2, Play, RotateCcw } from 'lucide-react';
import { api } from '../api';
import type { Portfolio } from '../types';

// ── Types ────────────────────────────────────────────────────────────

interface WizardState {
  portfolioId: string;
  name: string;
  optimizationType: string;
  objectives: {
    financing_cost_weight: number;
    refinancing_risk_weight: number;
    interest_rate_risk_weight: number;
    currency_risk_weight: number;
  };
  constraints: {
    max_financing_cost: number | null;
    max_refinancing_concentration: number | null;
    max_currency_exposure: number | null;
    max_floating_rate_exposure: number | null;
    min_liquidity: number | null;
  };
  scenarios: {
    include_named: string[];
    monte_carlo_count: number;
    monte_carlo_seed: number;
  };
  solverConfig: {
    solvers: string[];
    time_limit_seconds: number;
  };
}

const STEPS = [
  { id: 1, label: 'Portfolio & Name' },
  { id: 2, label: 'Objectives' },
  { id: 3, label: 'Constraints' },
  { id: 4, label: 'Review & Submit' },
];

const NAMED_SCENARIOS = [
  { id: 'base', label: 'Base Case', description: 'Current market conditions' },
  { id: 'ir_shock', label: 'Interest Rate Shock', description: '+200bps parallel shift' },
  { id: 'fx_shock', label: 'FX Shock', description: '15% currency depreciation' },
  { id: 'credit_spread', label: 'Credit Spread Widening', description: '+300bps spread increase' },
  { id: 'liquidity_shock', label: 'Liquidity Shock', description: 'Market liquidity freeze' },
];

const SOLVER_OPTIONS = [
  { id: 'greedy', label: 'Greedy', description: 'Fast heuristic' },
  { id: 'mean_variance', label: 'Mean-Variance', description: 'Classic portfolio theory' },
  { id: 'scenario_based', label: 'Scenario-Based', description: 'Monte Carlo optimized' },
  { id: 'milp', label: 'MILP (Exact)', description: 'Mixed-integer linear' },
];

const OPTIMIZATION_TYPES = [
  { id: 'minimize_cost', label: 'Minimize Cost', description: 'Reduce total financing cost' },
  { id: 'minimize_risk', label: 'Minimize Risk', description: 'Reduce portfolio risk exposure' },
  { id: 'maximize_return', label: 'Maximize Return', description: 'Optimize risk-adjusted returns' },
  { id: 'multi_objective', label: 'Multi-Objective', description: 'Balance cost and risk' },
];

// ── Helpers ───────────────────────────────────────────────────────────

function formatCurrency(value: number): string {
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

function weightsValid(o: WizardState['objectives']): boolean {
  const sum = o.financing_cost_weight + o.refinancing_risk_weight + o.interest_rate_risk_weight + o.currency_risk_weight;
  return Math.abs(sum - 1.0) < 0.01;
}

function normalizeWeights(o: WizardState['objectives']): WizardState['objectives'] {
  const sum = o.financing_cost_weight + o.refinancing_risk_weight + o.interest_rate_risk_weight + o.currency_risk_weight;
  if (sum === 0) return { financing_cost_weight: 0.25, refinancing_risk_weight: 0.25, interest_rate_risk_weight: 0.25, currency_risk_weight: 0.25 };
  return {
    financing_cost_weight: o.financing_cost_weight / sum,
    refinancing_risk_weight: o.refinancing_risk_weight / sum,
    interest_rate_risk_weight: o.interest_rate_risk_weight / sum,
    currency_risk_weight: o.currency_risk_weight / sum,
  };
}

// ── Main Component ────────────────────────────────────────────────────

export default function NewOptimizationPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const preselectedPortfolio = params.get('portfolio') ?? '';

  const [step, setStep] = useState(1);
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [loadingPortfolios, setLoadingPortfolios] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [state, setState] = useState<WizardState>({
    portfolioId: preselectedPortfolio,
    name: '',
    optimizationType: 'minimize_cost',
    objectives: {
      financing_cost_weight: 0.40,
      refinancing_risk_weight: 0.25,
      interest_rate_risk_weight: 0.20,
      currency_risk_weight: 0.15,
    },
    constraints: {
      max_financing_cost: null,
      max_refinancing_concentration: null,
      max_currency_exposure: null,
      max_floating_rate_exposure: null,
      min_liquidity: null,
    },
    scenarios: {
      include_named: ['base'],
      monte_carlo_count: 5000,
      monte_carlo_seed: 42,
    },
    solverConfig: {
      solvers: ['greedy', 'mean_variance', 'scenario_based'],
      time_limit_seconds: 300,
    },
  });

  const loadPortfolios = useCallback(async () => {
    setLoadingPortfolios(true);
    try {
      const res = await api.portfolios.list({ page_size: 100 });
      setPortfolios(res.data);
    } catch {
      // ignore
    } finally {
      setLoadingPortfolios(false);
    }
  }, []);

  useEffect(() => {
    void loadPortfolios();
  }, [loadPortfolios]);

  const selectedPortfolio = useMemo(
    () => portfolios.find((p) => p.id === state.portfolioId),
    [portfolios, state.portfolioId],
  );

  const canAdvance = useMemo(() => {
    switch (step) {
      case 1: return !!state.portfolioId && !!state.name.trim();
      case 2: return weightsValid(state.objectives);
      case 3: return true;
      case 4: return true;
      default: return false;
    }
  }, [step, state]);

  function updateState(patch: Partial<WizardState>) {
    setState((prev) => ({ ...prev, ...patch }));
  }

  function normalize() {
    updateState({ objectives: normalizeWeights(state.objectives) });
  }

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.optimizations.create({
        portfolio_id: state.portfolioId,
        name: state.name.trim(),
        optimization_type: state.optimizationType,
        objectives: state.objectives,
        constraints: Object.fromEntries(
          Object.entries(state.constraints).filter(([, v]) => v !== null),
        ),
        solver_config: state.solverConfig,
        scenario_config: {
          include_named: state.scenarios.include_named,
          num_scenarios: state.scenarios.monte_carlo_count,
          monte_carlo_seed: state.scenarios.monte_carlo_seed,
        },
        random_seed: state.scenarios.monte_carlo_seed,
      });
      navigate(`/optimizations`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create optimization');
    } finally {
      setSubmitting(false);
    }
  }

  // ── Step 1: Portfolio & Name ────────────────────────────────────────

  function renderStep1() {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div>
          <label htmlFor="opt-portfolio" style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
            Portfolio *
          </label>
          {loadingPortfolios ? (
            <div style={{ padding: 12, color: '#6b7280', fontSize: 13 }}>Loading portfolios...</div>
          ) : portfolios.length === 0 ? (
            <div style={{ padding: 12, color: '#6b7280', fontSize: 13 }}>
              No portfolios found. <Link to="/dashboard">Create one first</Link>.
            </div>
          ) : (
            <select
              id="opt-portfolio"
              value={state.portfolioId}
              onChange={(e) => updateState({ portfolioId: e.target.value })}
              style={{
                width: '100%', padding: '10px 12px', borderRadius: 8,
                border: '1px solid #e5e7eb', fontSize: 14, background: '#fff',
              }}
            >
              <option value="">Select a portfolio...</option>
              {portfolios.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.instruments?.length ?? 0} instruments)
                </option>
              ))}
            </select>
          )}
        </div>

        <div>
          <label htmlFor="opt-name" style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
            Run name *
          </label>
          <input
            id="opt-name"
            type="text"
            value={state.name}
            onChange={(e) => updateState({ name: e.target.value })}
            placeholder="e.g. Q1 2026 refinancing pass"
            style={{
              width: '100%', padding: '10px 12px', borderRadius: 8,
              border: '1px solid #e5e7eb', fontSize: 14,
            }}
          />
        </div>

        <div>
          <label htmlFor="opt-type" style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
            Optimization type
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {OPTIMIZATION_TYPES.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => updateState({ optimizationType: t.id })}
                style={{
                  padding: '10px 12px', borderRadius: 8, textAlign: 'left',
                  border: `2px solid ${state.optimizationType === t.id ? '#2563eb' : '#e5e7eb'}`,
                  background: state.optimizationType === t.id ? 'rgba(37,99,235,0.05)' : '#fff',
                  cursor: 'pointer',
                }}
              >
                <div style={{ fontWeight: 600, fontSize: 13 }}>{t.label}</div>
                <div style={{ fontSize: 11, color: '#6b7280' }}>{t.description}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ── Step 2: Objectives ──────────────────────────────────────────────

  function renderStep2() {
    const o = state.objectives;
    const sum = o.financing_cost_weight + o.refinancing_risk_weight + o.interest_rate_risk_weight + o.currency_risk_weight;
    const valid = weightsValid(o);

    const sliders = [
      { key: 'financing_cost_weight' as const, label: 'Financing Cost', color: '#2563eb' },
      { key: 'refinancing_risk_weight' as const, label: 'Refinancing Risk', color: '#dc2626' },
      { key: 'interest_rate_risk_weight' as const, label: 'Interest Rate Risk', color: '#d97706' },
      { key: 'currency_risk_weight' as const, label: 'Currency Risk', color: '#7c3aed' },
    ];

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div>
          <p style={{ fontSize: 13, color: '#6b7280', marginBottom: 4 }}>
            Assign weights to each risk dimension. Weights must sum to 1.0.
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>Total: {sum.toFixed(2)}</span>
            {!valid && (
              <span style={{ fontSize: 12, color: '#dc2626' }}>
                (must equal 1.00)
              </span>
            )}
            <button
              type="button"
              onClick={normalize}
              style={{
                marginLeft: 'auto', padding: '4px 10px', borderRadius: 6,
                border: '1px solid #e5e7eb', background: '#fff', cursor: 'pointer',
                fontSize: 12, display: 'flex', alignItems: 'center', gap: 4,
              }}
            >
              <RotateCcw size={12} /> Normalize
            </button>
          </div>
        </div>

        {sliders.map(({ key, label, color }) => (
          <div key={key}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: 13, fontWeight: 500 }}>{label}</span>
              <span style={{ fontSize: 13, fontWeight: 600, color }}>
                {(o[key] * 100).toFixed(0)}%
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={o[key]}
              onChange={(e) => updateState({ objectives: { ...o, [key]: parseFloat(e.target.value) } })}
              style={{ width: '100%', accentColor: color }}
            />
          </div>
        ))}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 8, marginTop: 8 }}>
          {sliders.map(({ key, label, color }) => (
            <div key={key} style={{ textAlign: 'center' }}>
              <div style={{ height: 4, borderRadius: 2, background: '#f3f4f6', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${o[key] * 100}%`, background: color, borderRadius: 2 }} />
              </div>
              <div style={{ fontSize: 10, color: '#6b7280', marginTop: 4 }}>{label.split(' ')[0]}</div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ── Step 3: Constraints ─────────────────────────────────────────────

  function renderStep3() {
    const c = state.constraints;

    const fields = [
      { key: 'max_financing_cost' as const, label: 'Max Financing Cost', unit: '%', placeholder: 'e.g. 8.5' },
      { key: 'max_refinancing_concentration' as const, label: 'Max Refi Concentration', unit: '%', placeholder: 'e.g. 30' },
      { key: 'max_currency_exposure' as const, label: 'Max Currency Exposure', unit: '%', placeholder: 'e.g. 40' },
      { key: 'max_floating_rate_exposure' as const, label: 'Max Floating Rate', unit: '%', placeholder: 'e.g. 50' },
      { key: 'min_liquidity' as const, label: 'Min Liquidity Reserve', unit: '%', placeholder: 'e.g. 10' },
    ];

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <p style={{ fontSize: 13, color: '#6b7280' }}>
          Set optional constraints. Leave empty for no limit.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {fields.map(({ key, label, unit, placeholder }) => (
            <div key={key}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
                {label}
              </label>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <input
                  type="number"
                  min={0}
                  max={100}
                  step={0.1}
                  value={c[key] ?? ''}
                  onChange={(e) => updateState({
                    constraints: { ...c, [key]: e.target.value ? parseFloat(e.target.value) : null },
                  })}
                  placeholder={placeholder}
                  style={{
                    flex: 1, padding: '8px 10px', borderRadius: 8,
                    border: '1px solid #e5e7eb', fontSize: 13,
                  }}
                />
                <span style={{ fontSize: 12, color: '#6b7280' }}>{unit}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Scenarios */}
        <div style={{ marginTop: 8 }}>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
            Named Scenarios
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
            {NAMED_SCENARIOS.map((s) => {
              const checked = state.scenarios.include_named.includes(s.id);
              return (
                <label
                  key={s.id}
                  style={{
                    display: 'flex', alignItems: 'flex-start', gap: 8,
                    padding: '8px 10px', borderRadius: 8, cursor: 'pointer',
                    border: `1px solid ${checked ? '#2563eb' : '#e5e7eb'}`,
                    background: checked ? 'rgba(37,99,235,0.05)' : '#fff',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => {
                      const named = checked
                        ? state.scenarios.include_named.filter((n) => n !== s.id)
                        : [...state.scenarios.include_named, s.id];
                      updateState({ scenarios: { ...state.scenarios, include_named: named } });
                    }}
                    style={{ marginTop: 2 }}
                  />
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600 }}>{s.label}</div>
                    <div style={{ fontSize: 11, color: '#6b7280' }}>{s.description}</div>
                  </div>
                </label>
              );
            })}
          </div>
        </div>

        {/* Monte Carlo */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
              Monte Carlo Count
            </label>
            <input
              type="range"
              min={1000}
              max={10000}
              step={1000}
              value={state.scenarios.monte_carlo_count}
              onChange={(e) => updateState({ scenarios: { ...state.scenarios, monte_carlo_count: parseInt(e.target.value) } })}
              style={{ width: '100%' }}
            />
            <div style={{ fontSize: 12, textAlign: 'center', fontWeight: 600 }}>
              {state.scenarios.monte_carlo_count.toLocaleString()} scenarios
            </div>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
              Random Seed
            </label>
            <input
              type="number"
              value={state.scenarios.monte_carlo_seed}
              onChange={(e) => updateState({ scenarios: { ...state.scenarios, monte_carlo_seed: parseInt(e.target.value) || 42 } })}
              style={{
                width: '100%', padding: '8px 10px', borderRadius: 8,
                border: '1px solid #e5e7eb', fontSize: 13,
              }}
            />
          </div>
        </div>

        {/* Solvers */}
        <div>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
            Solvers
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
            {SOLVER_OPTIONS.map((s) => {
              const checked = state.solverConfig.solvers.includes(s.id);
              return (
                <label
                  key={s.id}
                  style={{
                    display: 'flex', alignItems: 'flex-start', gap: 8,
                    padding: '8px 10px', borderRadius: 8, cursor: 'pointer',
                    border: `1px solid ${checked ? '#2563eb' : '#e5e7eb'}`,
                    background: checked ? 'rgba(37,99,235,0.05)' : '#fff',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => {
                      const solvers = checked
                        ? state.solverConfig.solvers.filter((n) => n !== s.id)
                        : [...state.solverConfig.solvers, s.id];
                      updateState({ solverConfig: { ...state.solverConfig, solvers } });
                    }}
                    style={{ marginTop: 2 }}
                  />
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600 }}>{s.label}</div>
                    <div style={{ fontSize: 11, color: '#6b7280' }}>{s.description}</div>
                  </div>
                </label>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // ── Step 4: Review ──────────────────────────────────────────────────

  function renderStep4() {
    const o = state.objectives;
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Portfolio */}
        <div className="panel" style={{ padding: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <p style={{ fontSize: 11, color: '#6b7280', textTransform: 'uppercase' }}>Portfolio</p>
              <p style={{ fontSize: 15, fontWeight: 600 }}>{selectedPortfolio?.name || state.portfolioId}</p>
            </div>
            <button type="button" onClick={() => setStep(1)} className="soft-button" style={{ fontSize: 12 }}>Edit</button>
          </div>
        </div>

        {/* Objectives */}
        <div className="panel" style={{ padding: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <p style={{ fontSize: 11, color: '#6b7280', textTransform: 'uppercase' }}>Objectives</p>
            <button type="button" onClick={() => setStep(2)} className="soft-button" style={{ fontSize: 12 }}>Edit</button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {[
              { label: 'Financing Cost', value: o.financing_cost_weight, color: '#2563eb' },
              { label: 'Refinancing Risk', value: o.refinancing_risk_weight, color: '#dc2626' },
              { label: 'Interest Rate', value: o.interest_rate_risk_weight, color: '#d97706' },
              { label: 'Currency', value: o.currency_risk_weight, color: '#7c3aed' },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 13 }}>{label}</span>
                <span style={{ fontSize: 13, fontWeight: 600, color }}>{(value * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* Constraints */}
        <div className="panel" style={{ padding: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <p style={{ fontSize: 11, color: '#6b7280', textTransform: 'uppercase' }}>Constraints</p>
            <button type="button" onClick={() => setStep(3)} className="soft-button" style={{ fontSize: 12 }}>Edit</button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
            {Object.entries(state.constraints).filter(([, v]) => v !== null).map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 13 }}>{k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</span>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{v}%</span>
              </div>
            ))}
            {Object.values(state.constraints).every((v) => v === null) && (
              <p style={{ fontSize: 13, color: '#9ca3af' }}>No constraints set</p>
            )}
          </div>
        </div>

        {/* Scenarios */}
        <div className="panel" style={{ padding: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <p style={{ fontSize: 11, color: '#6b7280', textTransform: 'uppercase' }}>Scenarios</p>
            <button type="button" onClick={() => setStep(3)} className="soft-button" style={{ fontSize: 12 }}>Edit</button>
          </div>
          <div style={{ fontSize: 13 }}>
            <p><strong>Named:</strong> {state.scenarios.include_named.join(', ') || 'None'}</p>
            <p><strong>Monte Carlo:</strong> {state.scenarios.monte_carlo_count.toLocaleString()} scenarios (seed: {state.scenarios.monte_carlo_seed})</p>
            <p><strong>Solvers:</strong> {state.solverConfig.solvers.join(', ')}</p>
          </div>
        </div>
      </div>
    );
  }

  // ── Render ──────────────────────────────────────────────────────────

  return (
    <div style={{ maxWidth: 680 }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Link to="/optimizations" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13, color: '#6b7280', textDecoration: 'none', marginBottom: 12 }}>
          <ArrowLeft size={14} /> Back to optimizations
        </Link>
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>New Optimization</h1>
      </div>

      {/* Step Indicator */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 24 }}>
        {STEPS.map((s, i) => (
          <div key={s.id} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
            <div style={{
              width: 32, height: 32, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 13, fontWeight: 700,
              background: step > s.id ? '#16a34a' : step === s.id ? '#2563eb' : '#e5e7eb',
              color: step >= s.id ? '#fff' : '#6b7280',
            }}>
              {step > s.id ? <Check size={14} /> : s.id}
            </div>
            <span style={{ fontSize: 11, color: step === s.id ? '#2563eb' : '#6b7280', fontWeight: step === s.id ? 600 : 400 }}>
              {s.label}
            </span>
          </div>
        ))}
      </div>

      {/* Step Content */}
      <div className="panel" style={{ padding: 24, marginBottom: 20 }}>
        {step === 1 && renderStep1()}
        {step === 2 && renderStep2()}
        {step === 3 && renderStep3()}
        {step === 4 && renderStep4()}
      </div>

      {/* Error */}
      {error && (
        <div style={{ padding: '10px 14px', borderRadius: 8, background: 'rgba(220,38,38,0.05)', border: '1px solid rgba(220,38,38,0.2)', marginBottom: 16 }}>
          <p style={{ color: '#dc2626', fontSize: 13 }}>{error}</p>
        </div>
      )}

      {/* Navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <button
          type="button"
          onClick={() => setStep((s) => Math.max(1, s - 1))}
          disabled={step === 1}
          className="soft-button"
          style={{ display: 'flex', alignItems: 'center', gap: 6, opacity: step === 1 ? 0.4 : 1 }}
        >
          <ArrowLeft size={14} /> Back
        </button>

        {step < 4 ? (
          <button
            type="button"
            onClick={() => setStep((s) => Math.min(4, s + 1))}
            disabled={!canAdvance}
            className="primary-button"
            style={{ display: 'flex', alignItems: 'center', gap: 6, opacity: canAdvance ? 1 : 0.4 }}
          >
            Next <ArrowRight size={14} />
          </button>
        ) : (
          <button
            type="button"
            onClick={() => void handleSubmit()}
            disabled={submitting}
            className="primary-button"
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}
          >
            {submitting ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Play size={14} />}
            {submitting ? 'Submitting...' : 'Run Optimization'}
          </button>
        )}
      </div>
    </div>
  );
}
