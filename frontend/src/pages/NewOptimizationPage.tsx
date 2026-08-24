import { useState, useEffect } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import type { Portfolio } from '../types';
import AppShell from '../components/layout/AppShell';
import Card, { CardHeader } from '../components/ui/Card';
import Button from '../components/ui/Button';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { useToast } from '../components/Toast';

export default function NewOptimizationPage() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [searchParams] = useSearchParams();
  const portfolioId = searchParams.get('portfolio') || '';
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState(portfolioId);
  const [name, setName] = useState('Public Debt Optimization');
  const [optType, setOptType] = useState('minimize_cost');
  const [numScenarios, setNumScenarios] = useState(10000);
  const [riskAversion, setRiskAversion] = useState(1.0);
  const [maxBudget, setMaxBudget] = useState('');
  const [maxSinglePct, setMaxSinglePct] = useState('');
  const [seed, setSeed] = useState(42);
  const [loading, setLoading] = useState(false);
  const [loadingPortfolios, setLoadingPortfolios] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.portfolios.list()
      .then((res) => setPortfolios((res as { data: Portfolio[] }).data || []))
      .catch(() => addToast('Failed to load portfolios', 'error'))
      .finally(() => setLoadingPortfolios(false));
  }, [addToast]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPortfolio) { setError('Select a portfolio'); return; }
    setError('');
    setLoading(true);
    try {
      const constraints: Record<string, unknown> = {};
      if (maxBudget) constraints.max_budget = parseFloat(maxBudget);
      if (maxSinglePct) constraints.max_single_instrument_pct = parseFloat(maxSinglePct);

      const job = await api.optimizations.create({
        portfolio_id: selectedPortfolio,
        name,
        optimization_type: optType,
        objectives: { type: optType, risk_aversion: riskAversion },
        constraints,
        solver_config: { solvers: ['greedy', 'mean_variance', 'scenario_based'] },
        scenario_config: { num_scenarios: numScenarios, horizon_years: 5 },
        random_seed: seed,
      });
      addToast('Optimization started', 'success');
      navigate(`/optimizations/${job.id}`);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to create optimization';
      setError(msg);
      addToast(msg, 'error');
    } finally {
      setLoading(false);
    }
  };

  if (loadingPortfolios) {
    return (
      <AppShell>
        <LoadingSpinner message="Loading portfolios..." />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="px-8 py-6 max-w-[900px] mx-auto">
        <div className="mb-8">
          <Link to="/" className="text-sm text-slate-500 hover:text-slate-700 mb-2 inline-block">&larr; Dashboard</Link>
          <h1 className="text-2xl font-bold text-slate-900">Create Optimization</h1>
          <p className="text-sm text-slate-500 mt-0.5">Configure and run a debt portfolio optimization</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <Card>
            <CardHeader title="Portfolio & Configuration" subtitle="Select a portfolio and optimization parameters" />
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Portfolio</label>
                <select
                  value={selectedPortfolio}
                  onChange={e => setSelectedPortfolio(e.target.value)}
                  required
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">Select a portfolio</option>
                  {portfolios.map(p => (
                    <option key={p.id} value={p.id}>{p.name} ({p.instruments?.length || 0} instruments)</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Optimization Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  required
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Optimization Type</label>
                <select
                  value={optType}
                  onChange={e => setOptType(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="minimize_cost">Minimize Cost</option>
                  <option value="minimize_risk">Minimize Risk</option>
                  <option value="mean_variance">Mean-Variance</option>
                  <option value="minimize_duration">Minimize Duration</option>
                  <option value="scenario_based">Scenario-Based</option>
                </select>
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader title="Scenario Parameters" subtitle="Configure Monte Carlo simulation" />
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Number of Scenarios</label>
                <input
                  type="number"
                  value={numScenarios}
                  onChange={e => setNumScenarios(parseInt(e.target.value))}
                  min={100}
                  max={50000}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Risk Aversion</label>
                <input
                  type="number"
                  value={riskAversion}
                  onChange={e => setRiskAversion(parseFloat(e.target.value))}
                  min={0}
                  max={10}
                  step={0.1}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Random Seed</label>
                <input
                  type="number"
                  value={seed}
                  onChange={e => setSeed(parseInt(e.target.value))}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader title="Constraints (Optional)" subtitle="Set limits on the optimization" />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Max Budget</label>
                <input
                  type="number"
                  value={maxBudget}
                  onChange={e => setMaxBudget(e.target.value)}
                  placeholder="e.g. 50000000000"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Max Single Instrument %</label>
                <input
                  type="number"
                  value={maxSinglePct}
                  onChange={e => setMaxSinglePct(e.target.value)}
                  min={0}
                  max={1}
                  step={0.01}
                  placeholder="0.0 - 1.0"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          </Card>

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="flex items-center gap-3">
            <Button type="submit" variant="primary" size="md" disabled={loading}>
              {loading ? 'Starting...' : 'Run Optimization'}
            </Button>
            <Link to="/">
              <Button variant="secondary" size="md">Cancel</Button>
            </Link>
          </div>
        </form>
      </div>
    </AppShell>
  );
}
