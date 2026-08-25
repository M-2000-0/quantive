import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AppShell from '../components/layout/AppShell';
import { Badge, Button, Card, EmptyState } from '../components/ui';
import { api } from '../api';
import type { Portfolio } from '../types';

function formatCurrency(value: number): string {
  if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  return `$${value.toLocaleString()}`;
}

const currencyBadgeVariant: Record<string, 'info' | 'success' | 'warning' | 'danger' | 'default'> = {
  USD: 'info',
  EUR: 'success',
  GBP: 'warning',
  JPY: 'danger',
};

export default function PortfolioListPage() {
  const navigate = useNavigate();
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.portfolios
      .list()
      .then((res) => setPortfolios((res as { data: Portfolio[] }).data || []))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, []);

  const getCurrencies = (p: Portfolio) => {
    const set = new Set(p.instruments.map((i) => i.currency));
    return Array.from(set);
  };

  const getTotalPrincipal = (p: Portfolio) =>
    p.instruments.reduce((sum, i) => sum + i.principal_outstanding, 0);

  const formatDate = (d: string) => {
    return new Date(d).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <AppShell>
      <div className="px-8 py-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Debt Portfolio</h1>
            <p className="mt-1 text-sm text-slate-500">
              Manage sovereign debt instruments and portfolio allocations
            </p>
          </div>
          <Button variant="primary" onClick={() => navigate('/portfolios/new')}>
            <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            New Portfolio
          </Button>
        </div>

        {loading && (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="glass-card p-6 animate-pulse">
                <div className="h-5 bg-white/60 rounded-xl w-1/3 mb-3" />
                <div className="h-4 bg-white/40 rounded-xl w-2/3 mb-4" />
                <div className="flex gap-2">
                  <div className="h-5 bg-white/40 rounded-full w-12" />
                  <div className="h-5 bg-white/40 rounded-full w-12" />
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && error && (
          <div className="glass-card border-red-200/40 bg-red-500/10 backdrop-blur-xl p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {!loading && !error && portfolios.length === 0 && (
          <Card>
            <EmptyState
              icon={
                <svg className="h-12 w-12" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 0H21m-1.5 0H21" />
                </svg>
              }
              title="No portfolios yet"
              description="Create your first debt portfolio to begin optimization analysis."
              action={{ label: 'Create Portfolio', onClick: () => navigate('/portfolios/new') }}
            />
          </Card>
        )}

        {!loading && !error && portfolios.length > 0 && (
          <div className="space-y-4">
            <div className="glass-card overflow-hidden p-0">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/40 bg-white/30 backdrop-blur-xl">
                    <th className="text-left px-6 py-3.5 text-[11px] font-bold text-slate-500 uppercase tracking-widest">
                      Name
                    </th>
                    <th className="text-left px-6 py-3.5 text-[11px] font-bold text-slate-500 uppercase tracking-widest">
                      Instruments
                    </th>
                    <th className="text-right px-6 py-3.5 text-[11px] font-bold text-slate-500 uppercase tracking-widest">
                      Total Principal
                    </th>
                    <th className="text-left px-6 py-3.5 text-[11px] font-bold text-slate-500 uppercase tracking-widest">
                      Currency Exposure
                    </th>
                    <th className="text-left px-6 py-3.5 text-[11px] font-bold text-slate-500 uppercase tracking-widest">
                      Created
                    </th>
                    <th className="text-right px-6 py-3.5 text-[11px] font-bold text-slate-500 uppercase tracking-widest">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/25">
                  {portfolios.map((portfolio) => {
                    const currencies = getCurrencies(portfolio);
                    const totalPrincipal = getTotalPrincipal(portfolio);
                    return (
                      <tr
                        key={portfolio.id}
                        onClick={() => navigate(`/portfolios/${portfolio.id}`)}
                        className="hover:bg-white/40 backdrop-blur-sm cursor-pointer transition-colors bg-white/15"
                      >
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-xl bg-white/60 border border-white/60 backdrop-blur-md flex items-center justify-center shadow-sm">
                              <svg className="h-4.5 w-4.5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                              </svg>
                            </div>
                            <div>
                              <p className="text-sm font-semibold tracking-tight text-slate-900">{portfolio.name}</p>
                              <p className="text-xs text-slate-500 truncate max-w-xs">
                                {portfolio.description || 'No description'}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className="text-sm font-medium text-slate-700">
                            {portfolio.instruments.length}
                          </span>
                          <span className="text-sm text-slate-400 ml-1">
                            {portfolio.instruments.length === 1 ? 'instrument' : 'instruments'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <span className="text-sm font-semibold text-slate-900">
                            {formatCurrency(totalPrincipal)}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            {currencies.map((c) => (
                              <Badge key={c} variant={currencyBadgeVariant[c] || 'default'} size="sm">
                                {c}
                              </Badge>
                            ))}
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className="text-sm text-slate-500">{formatDate(portfolio.created_at)}</span>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/portfolios/${portfolio.id}`);
                            }}
                          >
                            View
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="text-xs text-slate-400 text-right">
              {portfolios.length} {portfolios.length === 1 ? 'portfolio' : 'portfolios'}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
