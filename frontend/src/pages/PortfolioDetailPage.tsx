import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import AppShell from '../components/layout/AppShell';
import { Badge, Button, Card, StatCard, Modal } from '../components/ui';
import { api } from '../api';
import type { Portfolio } from '../types';

function formatCurrency(value: number): string {
  if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  return `$${value.toLocaleString()}`;
}

const typeBadge: Record<string, 'info' | 'success' | 'warning' | 'danger' | 'default' | 'outline'> = {
  treasury_bond: 'info',
  sovereign_bond: 'info',
  domestic_bond: 'default',
  floating_rate_note: 'warning',
  inflation_linked: 'success',
  t_bill: 'outline',
  concessional_loan: 'success',
  commercial_loan: 'danger',
};

export default function PortfolioDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!id) return;
    api.portfolios.get(id)
      .then(setPortfolio)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const handleDelete = async () => {
    if (!portfolio) return;
    setDeleting(true);
    try {
      await api.portfolios.delete(portfolio.id);
      navigate('/portfolios');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to delete');
    } finally {
      setDeleting(false);
      setDeleteModalOpen(false);
    }
  };

  if (loading) {
    return (
      <AppShell>
        <div className="px-8 py-6 max-w-7xl mx-auto animate-pulse space-y-6">
          <div className="h-5 bg-slate-200 rounded w-64" />
          <div className="h-8 bg-slate-200 rounded w-96" />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => <div key={i} className="h-24 bg-slate-100 rounded-lg" />)}
          </div>
          <div className="h-64 bg-slate-100 rounded-lg" />
        </div>
      </AppShell>
    );
  }

  if (error) return <AppShell><div className="px-8 py-6 max-w-7xl mx-auto"><div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">{error}</div></div></AppShell>;
  if (!portfolio) return <AppShell><div className="px-8 py-6 max-w-7xl mx-auto text-sm text-slate-500">Portfolio not found</div></AppShell>;

  const totalPrincipal = portfolio.instruments.reduce((s, i) => s + i.principal_outstanding, 0);
  const avgCoupon = portfolio.instruments.length > 0
    ? portfolio.instruments.reduce((s, i) => s + i.coupon_rate, 0) / portfolio.instruments.length
    : 0;
  const currencies = Array.from(new Set(portfolio.instruments.map((i) => i.currency)));
  const avgMaturity = portfolio.instruments.length > 0
    ? portfolio.instruments.reduce((s, i) => {
        const years = (new Date(i.maturity_date).getTime() - Date.now()) / (365.25 * 24 * 60 * 60 * 1000);
        return s + Math.max(0, years);
      }, 0) / portfolio.instruments.length
    : 0;

  const Breadcrumb = () => (
    <nav className="flex items-center gap-1.5 text-sm mb-6">
      <button onClick={() => navigate('/')} className="text-slate-500 hover:text-slate-700 transition-colors">Dashboard</button>
      <svg className="h-4 w-4 text-slate-300" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" /></svg>
      <button onClick={() => navigate('/portfolios')} className="text-slate-500 hover:text-slate-700 transition-colors">Portfolios</button>
      <svg className="h-4 w-4 text-slate-300" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" /></svg>
      <span className="font-medium text-slate-900">{portfolio.name}</span>
    </nav>
  );

  return (
    <AppShell>
      <div className="px-8 py-6 max-w-7xl mx-auto">
        <Breadcrumb />

        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{portfolio.name}</h1>
            {portfolio.description && (
              <p className="mt-1 text-sm text-slate-500 max-w-2xl">{portfolio.description}</p>
            )}
            <div className="flex items-center gap-3 mt-2">
              <span className="text-xs text-slate-400">Created {new Date(portfolio.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
              <span className="text-xs text-slate-300">&middot;</span>
              <span className="text-xs text-slate-400">{portfolio.instruments.length} instruments</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="primary" onClick={() => navigate(`/optimizations/new?portfolio=${portfolio.id}`)}>
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605" />
              </svg>
              Run Optimization
            </Button>
            <Button variant="secondary" onClick={() => setDeleteModalOpen(true)}>
              <svg className="h-4 w-4 text-red-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
              </svg>
              Delete
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard label="Total Principal" value={formatCurrency(totalPrincipal)} icon={
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          } />
          <StatCard label="Avg Coupon" value={`${(avgCoupon * 100).toFixed(2)}%`} icon={
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
          } />
          <StatCard label="Currencies" value={currencies.length} icon={
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0012 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75z" />
            </svg>
          } />
          <StatCard label="Avg Maturity" value={`${avgMaturity.toFixed(1)} yrs`} icon={
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
            </svg>
          } />
        </div>

        <Card padding={false}>
          <div className="px-6 py-4 border-b border-white/40">
            <h2 className="text-base font-semibold text-slate-900">Instruments ({portfolio.instruments.length})</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/40 bg-white/30 backdrop-blur-xl">
                  {['Name', 'Type', 'Currency', 'Principal', 'Coupon', 'Maturity', 'Spread', 'Callable'].map((h) => (
                    <th key={h} className={`px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider ${['Principal', 'Coupon', 'Spread'].includes(h) ? 'text-right' : h === 'Callable' ? 'text-center' : 'text-left'}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/25">
                {portfolio.instruments.map((inst) => (
                  <tr key={inst.id} className="hover:bg-white/40/50 transition-colors">
                    <td className="px-6 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0">
                          <svg className="h-4 w-4 text-slate-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                          </svg>
                        </div>
                        <span className="font-medium text-slate-900 truncate max-w-[240px]">{inst.name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-3.5">
                      <Badge variant={typeBadge[inst.instrument_type] || 'default'} size="sm">
                        {inst.instrument_type.replace(/_/g, ' ')}
                      </Badge>
                    </td>
                    <td className="px-6 py-3.5"><Badge variant="info" size="sm">{inst.currency}</Badge></td>
                    <td className="px-6 py-3.5 text-right font-medium text-slate-900">{formatCurrency(inst.principal_outstanding)}</td>
                    <td className="px-6 py-3.5 text-right text-slate-700">{(inst.coupon_rate * 100).toFixed(2)}%</td>
                    <td className="px-6 py-3.5 text-slate-600 whitespace-nowrap">{inst.maturity_date}</td>
                    <td className="px-6 py-3.5 text-right text-slate-700">{inst.spread_bps} bps</td>
                    <td className="px-6 py-3.5 text-center">
                      {inst.is_callable ? (
                        <Badge variant="warning" size="sm">Callable</Badge>
                      ) : (
                        <span className="text-xs text-slate-400">&mdash;</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <Modal isOpen={deleteModalOpen} onClose={() => setDeleteModalOpen(false)} title="Delete Portfolio" size="sm">
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            Are you sure you want to delete <strong>{portfolio.name}</strong>? This action cannot be undone.
            All {portfolio.instruments.length} instruments will be permanently removed.
          </p>
          <div className="flex justify-end gap-3">
            <Button variant="secondary" size="sm" onClick={() => setDeleteModalOpen(false)}>Cancel</Button>
            <Button variant="danger" size="sm" loading={deleting} onClick={handleDelete}>Delete Portfolio</Button>
          </div>
        </div>
      </Modal>
    </AppShell>
  );
}
