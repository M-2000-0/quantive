import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  ArrowUpRight, Calendar, AlertCircle, CheckCircle, Mail, Search, Shield, Info,
  Wallet, BarChart2, TrendingUp
} from 'lucide-react';
import { api } from '../api';
import type { DashboardSummary } from '../types';

function formatCurrency(value: number): string {
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [deductionSummary, setDeductionSummary] = useState<{
    total_deductions: number;
    estimated_savings: number;
    standard_vs_itemized: string;
    deductions_found: number;
    next_actions: { title: string; amount: number; priority: string }[];
  } | null>(null);
  const [sprintStatus, setSprintStatus] = useState<{
    days_remaining: number;
    total_potential_savings: number;
    actions_taken: number;
    actions_remaining: number;
    actions: any[];
    urgency_message: string;
  } | null>(null);
  const [notificationsCount, setNotificationsCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [params] = useSearchParams();
  const searchQuery = (params.get('q') ?? '').trim().toLowerCase();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const summaryData = await api.dashboard.summary();
      const dedData = await api.deductions.summary();
      const sprintData = await api.sprint.status();
      const notifData = await api.notifications.summary();

      setSummary(summaryData);
      setDeductionSummary({
        total_deductions: dedData.total_deductions || 0,
        estimated_savings: dedData.estimated_savings || 0,
        standard_vs_itemized: dedData.standard_vs_itemized || '—',
        deductions_found: dedData.deductions_found?.length || 0,
        next_actions: dedData.next_actions || [],
      });

      setSprintStatus({
        days_remaining: sprintData.days_remaining,
        total_potential_savings: sprintData.total_potential_savings,
        actions_taken: sprintData.actions_taken,
        actions_remaining: sprintData.actions_remaining,
        actions: sprintData.actions,
        urgency_message: sprintData.urgency_message,
      });

      setNotificationsCount(notifData.unread_count || 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Format helpers
  const formatNumber = (num: number): string => num.toLocaleString();

  // Compute derived values early
  const deductionActions = useMemo(() => {
    return deductionSummary?.next_actions || [];
  }, [deductionSummary]);

  const sprintActions = useMemo(() => {
    return sprintStatus?.actions || [];
  }, [sprintStatus]);

  // Urgency banner if tax sprint is active
  const hasUrgency = sprintStatus && sprintStatus.days_remaining > 0 && sprintStatus.days_remaining <= 60;

  // Dedction summary card HTML
  const deductionCardContent = deductionSummary ? (
    <p style={{ marginBottom: 8, fontSize: 13 }}>
      <Info className="mr-1 size-3" /> Estimated savings: {formatCurrency(deductionSummary.estimated_savings)}
    </p>
    <p style={{ fontSize: 12, color: '#6b7280' }}>
      Standard vs Itemized: {deductionSummary.standard_vs_itemized}
    </p>
    <p style={{ fontSize: 12, color: '#6b7280' }}>
      {deductionSummary.deductions_found} deductions found from transactions
    </p>
  ) : (
    <p style={{ marginBottom: 8, fontSize: 13, color: '#6b7280' }}>
      Connect accounts to detect tax-saving opportunities
    </p>
  );

  // Sprint progress card content HTML
  const sprintCardContent = sprintStatus ? (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span>Completed:</span> {sprintStatus.actions_taken}
        <span>Remaining:</span> {sprintStatus.actions_remaining}
      </div>
      {sprintStatus.urgency_message && (
        <p style={{ color: '#dc2626', fontSize: 12, marginBottom: 8 }}>
          {sprintStatus.urgency_message}
        </div>
      )}
      {sprintActions.length > 0 && (
        <p style={{ fontSize: 12, color: '#055957' }}>
          <strong>Key moves:</strong> {sprintActions.slice(0, 3).map((a: any) => (
            <span key={a.id} style={{ marginRight: 8 }}>
              {a.title}: {a.estimated_savings > 0 ? formatCurrency(a.estimated_savings) : 'TBD'} — {a.days_left} days left
            </span>
          ))}…</p>
      )}
    </div>
  ) : (
    <p>November 1 — Year-end tax planning window open</p>
  );

  // Notifications badge
  const notifBadge = notificationsCount > 0 ? (
    <span style={{ marginLeft: 8, background: '#059669', color: 'white', borderRadius: 9999, padding: '2px 6', fontSize: 12 }}>
      {notificationsCount}
    </span>
  ) : null;

  // Format number with commas
  const formatNumber = (num: number): string => num.toLocaleString();

  // Compute derived values early
  const deductionActionsList = useMemo(() => {
    return deductionSummary?.next_actions || [];
  }, [deductionSummary]);

  const sprintActionsList = useMemo(() => {
    return sprintStatus?.actions || [];
  }, [sprintStatus]);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', color: '#6b7280' }}>
          <BarChart2 size={32} className="animate-spin" /> Loading dashboard…
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', maxWidth: 400 }}>
          <p style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, color: '#dc2626' }}>Failed to load dashboard</p>
          <p style={{ color: '#6b7280', marginBottom: 16 }}>{error}</p>
          <button
            type="button"
            onClick={() => void load()}
            style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#fff', cursor: 'pointer', fontWeight: 500 }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4">
      {hasUrgency && (
        <div style={{ marginBottom: 16, padding: '12px 16px', borderRadius: 8, background: '#fee2e2', border: '#fecaca', color: '#dc2626', fontSize: 13 }}>
          <Info className="mr-2 size-4" /> {hasUrgency ? 'Urgent: ' : ''}Year-end tax action needed
        </div>
      )}

      <div className="rounded-lg border border-orange-500/20 bg-orange-50/30 p-4">
        <h2 className="font-medium text-orange-600 mb-2">Year-End Tax Sprint</h2>
        {sprintStatus ? (
          <div className="space-y-2 text-sm">
            <div className="flex justify-between items-center">
              <span>Completed:</span> {sprintStatus.actions_taken}
              <span>Remaining:</span> {sprintStatus.actions_remaining}
            </div>
            {sprintStatus.urgency_message && (
              <p className="text-orange-600 text-sm">{sprintStatus.urgency_message}</p>
            )}
            {sprintActions.length > 0 && (
              <p className="text-orange-500 text-xs">
                <strong>Key moves:</strong> {sprintActions.slice(0, 3).map((a: any) => (
                  <span key={a.id} className="mr-2">
                    {a.title}: {a.estimated_savings > 0 ? formatCurrency(a.estimated_savings) : 'TBD'} — {a.days_left} days left
                  </span>
                ))}…</p>
            )}
          </div>
        ) : (
          <p className="text-orange-500 text-sm">November 1 — Year-end tax planning window open</p>
        )}
      </div>

      <div className="rounded-lg border-emerald-500/20 bg-emerald-50/30 p-4">
        <h2 className="font-medium text-emerald-600 mb-2">Notifications <AlertCircle className="mr-2 size-4" /> {notificationsCount}</h2>
        {notificationsCount > 0 ? (
          <p className="text-emerald-600 text-sm">
            You have {notificationsCount} unread notification{'s' if notificationsCount > 1 else ''}.
            <Link className="underline underline-offset-2 text-emerald-600 hover:text-emerald-500" to="/notifications">
              View all notifications
            </Link>
          </p>
        ) : (
          <p className="text-gray-500 text-sm">No new notifications.</p>
        )}
      </div>

      <div className="flex items-center">
        <InfoCircle className="mr-2 size-3 text-primary" /> {deductionSummary?.deductions_found > 0 ? `${deductionSummary.deductions_found} deductions detected` : ''}{' '}
        {sprintStatus?.days_remaining > 0 ? `${sprintStatus.days_remaining}d remaining sprint` : ''}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s, i) => (
          <div key={i} className="border rounded-lg p-3 hover:bg-gray-50 transition-colors">
            <div className="flex items-start">
              <span className="text-xl font-medium">{s.value}</span>
              <div className="ml-3 flex-1">
                <p className="text-sm font-medium">{s.label}</p>
                <p className="text-xs text-gray-500">{s.title || ''}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {summary && summary.portfolio_count === 0 && (
        <section className="mt-6 border border-blue-500/20 bg-blue-50/30 p-6">
          <h2 className="font-medium text-blue-600 mb-2">Get started</h2>
          <p className="text-blue-600 text-sm mb-3">
            1. Add a portfolio &nbsp;→&nbsp; 2. Run an optimization &nbsp;→&nbsp; 3. Review risk.
            Load the demo portfolio or create your own — two minutes either way.
          </p>
          <div className="flex gap-2 flex-wrap">
            <button className="primary-button">Load demo portfolio →</button>
            <Link className="soft-button" href="/portfolios">Create portfolio</Link>
            <Link className="soft-button" href="/optimizations/new">Run optimization</Link>
          </div>
        </section>
      )}
    </div>
  );
}

function hasUrgency(sprintStatus: any): boolean {
  return sprintStatus && sprintStatus.days_remaining > 0 && sprintStatus.days_remaining <= 60;
}