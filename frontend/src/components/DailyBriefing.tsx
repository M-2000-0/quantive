import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  Bell,
  CalendarClock,
  CheckCircle,
  Clock,
  FileText,
  Loader2,
  RefreshCw,
  TrendingUp,
  Zap } from 'lucide-react';
import { api } from '../api';

// ── Types ──────────────────────────────────────────────────────────

interface BriefingItem {
  category: string;
  priority: string;
  title: string;
  detail: string;
  action_label: string;
  action_url: string;
  icon: string;
  metadata?: Record<string, unknown>;
}

interface MaturityItem {
  id: string;
  name: string;
  currency: string;
  principal: number;
  coupon_rate: number;
  maturity_date: string;
  days_until_maturity: number;
  portfolio_id: string;
  urgency: string;
}

interface Briefing {
  briefing_message: string;
  items: BriefingItem[];
  item_count: number;
  critical_count: number;
  high_count: number;
  upcoming_maturities: MaturityItem[];
  total_maturity_value_usd: number;
  notifications: {
    unread_count: number;
    recent: Array<{
      id: string;
      type: string;
      title: string;
      message: string;
      created_at: string | null;
    }>;
  };
  generated_at: string;
}

// ── Helpers ─────────────────────────────────────────────────────────

function formatCurrency(value: number): string {
  if (value >= 1e12) return `$${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

function priorityColor(priority: string): string {
  switch (priority) {
    case 'critical': return '#dc2626';
    case 'high': return '#ea580c';
    case 'medium': return '#d97706';
    default: return '#6b7280';
  }
}

function priorityBg(priority: string): string {
  switch (priority) {
    case 'critical': return '#fef2f2';
    case 'high': return '#fff7ed';
    case 'medium': return '#fffbeb';
    default: return '#f9fafb';
  }
}

function categoryIcon(category: string): string {
  switch (category) {
    case 'maturity': return '⏰';
    case 'optimization_running': return '🔄';
    case 'optimization_completed': return '✅';
    case 'first_optimization': return '⚡';
    case 'yield_curve_inversion': return '📊';
    case 'watchlist_update': return '👁️';
    default: return '📋';
  }
}

// ── Component ───────────────────────────────────────────────────────

export default function DailyBriefing() {
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedItem, setExpandedItem] = useState<number | null>(null);

  const loadBriefing = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.briefing.get() as Briefing;
      setBriefing(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load briefing');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadBriefing();
  }, [loadBriefing]);

  if (loading && !briefing) {
    return (
      <div style={containerStyle}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
          <Loader2 size={20} style={{ animation: 'spin 1s linear infinite', color: '#6366f1' }} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={containerStyle}>
        <div style={{ textAlign: 'center', padding: 20, color: '#dc2626', fontSize: 13 }}>{error}</div>
        <div style={{ textAlign: 'center', paddingBottom: 16 }}>
          <button
            type="button"
            onClick={() => void loadBriefing()}
            style={{ padding: '6px 16px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 500 }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!briefing) return null;

  return (
    <div className="daily-briefing" id="briefing" style={containerStyle}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Bell size={18} color="#6366f1" />
          <h3 style={{ fontSize: 16, fontWeight: 600, color: '#111827', margin: 0 }}>Daily Briefing</h3>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {briefing.notifications.unread_count > 0 && (
            <span style={unreadBadgeStyle}>
              {briefing.notifications.unread_count} unread
            </span>
          )}
          <button
            type="button"
            onClick={loadBriefing}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#6b7280' }}
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* Briefing Message */}
      <div style={messageCardStyle}>
        <p style={{ fontSize: 14, color: '#374151', margin: 0, lineHeight: 1.5 }}>
          {briefing.briefing_message}
        </p>
      </div>

      {/* Quick Stats */}
      <div className="qa-grid-3" style={{ display: 'grid', gap: 8, marginBottom: 16 }}>
        <div style={quickStatStyle}>
          <span style={{ fontSize: 18, fontWeight: 700, color: '#111827' }}>{briefing.item_count}</span>
          <span style={{ fontSize: 11, color: '#6b7280' }}>Action Items</span>
        </div>
        <div style={quickStatStyle}>
          <span style={{ fontSize: 18, fontWeight: 700, color: '#dc2626' }}>{briefing.critical_count}</span>
          <span style={{ fontSize: 11, color: '#6b7280' }}>Critical</span>
        </div>
        <div style={quickStatStyle}>
          <span style={{ fontSize: 18, fontWeight: 700, color: '#f59e0b' }}>
            {briefing.upcoming_maturities.length}
          </span>
          <span style={{ fontSize: 11, color: '#6b7280' }}>Maturities (90d)</span>
        </div>
      </div>

      {/* Upcoming Maturities (if any) */}
      {briefing.upcoming_maturities.length > 0 && (
        <div style={sectionStyle}>
          <div style={sectionHeaderStyle}>
            <CalendarClock size={14} color="#ea580c" />
            <span style={sectionTitleStyle}>Upcoming Maturities</span>
            <span style={{ fontSize: 11, color: '#9ca3af' }}>
              {formatCurrency(briefing.total_maturity_value_usd)} total
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {briefing.upcoming_maturities.slice(0, 5).map((m) => (
              <div
                key={m.id}
                style={{
                  ...maturityRowStyle,
                  borderLeftColor: m.urgency === 'critical' ? '#dc2626' : '#f59e0b' }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, color: '#111827', fontSize: 13 }}>{m.name}</div>
                  <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>
                    {formatCurrency(m.principal)} {m.currency} • {m.coupon_rate}% coupon
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: m.urgency === 'critical' ? '#dc2626' : '#d97706' }}>
                    {m.days_until_maturity}d
                  </div>
                  <div style={{ fontSize: 10, color: '#9ca3af' }}>{m.maturity_date}</div>
                </div>
                <Link
                  to="/optimizations/new"
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: '#6366f1',
                    textDecoration: 'none',
                    whiteSpace: 'nowrap' }}
                >
                  Pre-fund →
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action Items */}
      <div style={sectionStyle}>
        <div style={sectionHeaderStyle}>
          <Zap size={14} color="#6366f1" />
          <span style={sectionTitleStyle}>Action Items</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {briefing.items.slice(0, 8).map((item, idx) => (
            <article
              key={idx}
              style={{
                ...actionItemStyle,
                background: expandedItem === idx ? priorityBg(item.priority) : '#fff' }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                <span style={{ fontSize: 18, lineHeight: 1 }} aria-hidden="true">{item.icon || categoryIcon(item.category)}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                    <span style={{ fontWeight: 600, color: '#111827', fontSize: 13 }}>{item.title}</span>
                    <span
                      style={{
                        fontSize: 10,
                        fontWeight: 600,
                        padding: '1px 6px',
                        borderRadius: 4,
                        background: priorityBg(item.priority),
                        color: priorityColor(item.priority),
                        textTransform: 'uppercase',
                        whiteSpace: 'nowrap' }}
                    >
                      {item.priority}
                    </span>
                  </div>
                  <p style={{ fontSize: 12, color: '#6b7280', margin: '4px 0 0', lineHeight: 1.4 }}>
                    {item.detail}
                  </p>
                  <button
                    type="button"
                    onClick={() => setExpandedItem(expandedItem === idx ? null : idx)}
                    aria-expanded={expandedItem === idx}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#6366f1', fontSize: 12, fontWeight: 600, padding: '4px 0' }}
                  >
                    {expandedItem === idx ? 'Hide details' : 'Show details'}
                  </button>
                  {expandedItem === idx && (
                    <a
                      href={item.action_url}
                      onClick={(e) => e.stopPropagation()}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 4,
                        marginTop: 8,
                        marginLeft: 8,
                        padding: '6px 12px',
                        borderRadius: 6,
                        background: '#6366f1',
                        color: '#fff',
                        fontSize: 12,
                        fontWeight: 600,
                        textDecoration: 'none' }}
                    >
                      {item.action_label}
                      <ArrowRight size={12} />
                    </a>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>

      {/* Recent Notifications */}
      {briefing.notifications.recent.length > 0 && (
        <div style={sectionStyle}>
          <div style={sectionHeaderStyle}>
            <Bell size={14} color="#6b7280" />
            <span style={sectionTitleStyle}>Recent Notifications</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {briefing.notifications.recent.map((n) => (
              <div key={n.id} style={notificationRowStyle}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 500, color: '#111827', fontSize: 13 }}>{n.title}</div>
                  <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>{n.message}</div>
                </div>
                {n.created_at && (
                  <span style={{ fontSize: 10, color: '#9ca3af', whiteSpace: 'nowrap' }}>
                    {new Date(n.created_at).toLocaleTimeString()}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <div style={{ marginTop: 12, fontSize: 11, color: '#9ca3af', textAlign: 'center' }}>
        Generated {new Date(briefing.generated_at).toLocaleTimeString()} • Click items for actions
      </div>
    </div>
  );
}

// ── Styles ───────────────────────────────────────────────────────

const containerStyle: React.CSSProperties = {
  background: '#fff',
  borderRadius: 12,
  padding: 20,
  border: '1px solid #e5e7eb' };

const messageCardStyle: React.CSSProperties = {
  background: '#f9fafb',
  borderRadius: 8,
  padding: 14,
  marginBottom: 16,
  border: '1px solid #f3f4f6' };

const quickStatStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  padding: 10,
  background: '#f9fafb',
  borderRadius: 8 };

const sectionStyle: React.CSSProperties = {
  marginBottom: 14 };

const sectionHeaderStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  marginBottom: 8 };

const sectionTitleStyle: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  color: '#374151',
  flex: 1 };

const maturityRowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 12,
  padding: 10,
  background: '#f9fafb',
  borderRadius: 8,
  borderLeft: '3px solid #e5e7eb' };

const actionItemStyle: React.CSSProperties = {
  padding: 10,
  borderRadius: 8,
  border: '1px solid #f3f4f6',
  cursor: 'pointer',
  transition: 'all 0.15s' };

const notificationRowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: 8,
  background: '#f9fafb',
  borderRadius: 6 };

const unreadBadgeStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 600,
  color: '#dc2626',
  background: '#fef2f2',
  padding: '2px 8px',
  borderRadius: 99 };
