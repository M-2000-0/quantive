import { useState, useEffect } from 'react';
import { api } from '../api';
import AppShell from '../components/layout/AppShell';
import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import LoadingSpinner from '../components/ui/LoadingSpinner';

type Tab = 'overview' | 'threats' | 'audit';

interface SecurityDashboard {
  security_score: number;
  threat_status: { blocked_ips: number; failed_logins: number; status: string };
  audit_events_24h: Record<string, number>;
  user_stats: { total: number; active: number; inactive: number };
  recommendations: Array<{ severity: string; message: string; action: string }>;
}

interface AuditEvent {
  id: string;
  actor_email: string;
  action: string;
  ip_address: string;
  created_at: string;
}

function ScoreGauge({ score }: { score: number }) {
  const color = score >= 90 ? '#22c55e' : score >= 70 ? '#eab308' : score >= 50 ? '#f97316' : '#ef4444';
  const label = score >= 90 ? 'Excellent' : score >= 70 ? 'Good' : score >= 50 ? 'Fair' : 'Poor';
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <svg width="140" height="140" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r="54" fill="none" stroke="#e2e8f0" strokeWidth="8" />
        <circle
          cx="60" cy="60" r="54" fill="none"
          stroke={color} strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 60 60)"
          style={{ transition: 'stroke-dashoffset 1s ease-out' }}
        />
        <text x="60" y="56" textAnchor="middle" className="text-2xl font-bold" fill={color}>
          {score}
        </text>
        <text x="60" y="72" textAnchor="middle" className="text-xs" fill="#64748b">
          {label}
        </text>
      </svg>
    </div>
  );
}

function RecommendationCard({ rec }: { rec: { severity: string; message: string; action: string } }) {
  const severityStyles: Record<string, { bg: string; border: string; icon: string; badge: 'danger' | 'warning' | 'info' | 'success' }> = {
    high: { bg: 'bg-red-50', border: 'border-red-200', icon: '🔴', badge: 'danger' },
    medium: { bg: 'bg-amber-50', border: 'border-amber-200', icon: '⚠️', badge: 'warning' },
    low: { bg: 'bg-blue-50', border: 'border-blue-200', icon: 'ℹ️', badge: 'info' },
    info: { bg: 'bg-emerald-50', border: 'border-emerald-200', icon: '✅', badge: 'success' },
  };
  const s = severityStyles[rec.severity] || severityStyles.info;

  return (
    <div className={`${s.bg} ${s.border} border rounded-lg p-4`}>
      <div className="flex items-start gap-3">
        <span className="text-lg mt-0.5">{s.icon}</span>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant={s.badge}>{rec.severity.toUpperCase()}</Badge>
          </div>
          <p className="text-sm font-medium text-slate-900">{rec.message}</p>
          <p className="text-xs text-slate-500 mt-1">{rec.action}</p>
        </div>
      </div>
    </div>
  );
}

export default function SecurityDashboardPage() {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<SecurityDashboard | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [blockedIps, setBlockedIps] = useState<Array<{ ip: string; unblocks_at: string; remaining_seconds: number }>>([]);
  const [failedLogins, setFailedLogins] = useState<Array<{ ip: string; attempts: number; emails_targeted: string[]; last_attempt: string }>>([]);

  useEffect(() => {
    api.security.dashboard()
      .then(setDashboard)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (activeTab === 'audit') {
      api.security.auditTrail({ hours: 24 }).then(r => setAuditEvents(r.events)).catch(() => {});
    }
    if (activeTab === 'threats') {
      api.security.blockedIps().then(r => setBlockedIps(r.blocked_ips)).catch(() => {});
      api.security.failedLogins(24).then(r => setFailedLogins(r.failed_logins)).catch(() => {});
    }
  }, [activeTab]);

  const handleUnblock = async (ip: string) => {
    try {
      await api.security.unblockIp(ip);
      setBlockedIps(prev => prev.filter(b => b.ip !== ip));
    } catch {}
  };

  if (loading) return <AppShell><LoadingSpinner message="Loading security dashboard..." /></AppShell>;

  const tabs: { key: Tab; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '🛡️' },
    { key: 'threats', label: 'Threats', icon: '🚨' },
    { key: 'audit', label: 'Audit Trail', icon: '📋' },
  ];

  return (
    <AppShell>
      <div className="px-8 py-6 max-w-[1440px] mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Security Dashboard</h1>
            <p className="text-sm text-slate-500 mt-0.5">Monitor threats, audit events, and system security posture</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            <span className="text-xs font-medium text-emerald-700">All Systems Operational</span>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-slate-100 rounded-lg p-1 w-fit">
          {tabs.map(tab => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
                activeTab === tab.key ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              }`}>
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && dashboard && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <Card>
                <div className="text-center py-4">
                  <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">Security Score</h3>
                  <ScoreGauge score={dashboard.security_score} />
                </div>
              </Card>

              <Card>
                <CardHeader title="Threat Status" subtitle="Current threat level" />
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600">Status</span>
                    <Badge variant={dashboard.threat_status.status === 'healthy' ? 'success' : 'danger'}>
                      {dashboard.threat_status.status.toUpperCase()}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600">Blocked IPs</span>
                    <span className="text-sm font-bold text-slate-900">{dashboard.threat_status.blocked_ips}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600">Failed Logins (24h)</span>
                    <span className="text-sm font-bold text-slate-900">{dashboard.threat_status.failed_logins}</span>
                  </div>
                </div>
              </Card>

              <Card>
                <CardHeader title="User Accounts" subtitle="Account status overview" />
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600">Total Users</span>
                    <span className="text-sm font-bold text-slate-900">{dashboard.user_stats.total}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600">Active</span>
                    <span className="text-sm font-bold text-emerald-700">{dashboard.user_stats.active}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600">Inactive</span>
                    <span className="text-sm font-bold text-amber-700">{dashboard.user_stats.inactive}</span>
                  </div>
                </div>
              </Card>
            </div>

            {/* Audit Events 24h */}
            <Card>
              <CardHeader title="Activity (Last 24 Hours)" subtitle="Audit event breakdown by action type" />
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
                {Object.entries(dashboard.audit_events_24h).map(([action, count]) => (
                  <div key={action} className="bg-white/30 backdrop-blur-xl rounded-2xl border border-white/30 p-3 border border-white/25">
                    <p className="text-xs font-medium text-slate-500 truncate">{action.replace(/_/g, ' ')}</p>
                    <p className="text-lg font-bold text-slate-900 tabular-nums mt-1">{count}</p>
                  </div>
                ))}
                {Object.keys(dashboard.audit_events_24h).length === 0 && (
                  <p className="text-sm text-slate-400 col-span-full text-center py-4">No events in the last 24 hours</p>
                )}
              </div>
            </Card>

            {/* Recommendations */}
            <Card>
              <CardHeader title="Security Recommendations" subtitle="Prioritized actions to improve security" />
              <div className="space-y-3">
                {dashboard.recommendations.map((rec, i) => (
                  <RecommendationCard key={i} rec={rec} />
                ))}
              </div>
            </Card>
          </div>
        )}

        {/* Threats Tab */}
        {activeTab === 'threats' && (
          <div className="space-y-6">
            <Card>
              <CardHeader title="Blocked IP Addresses" subtitle="IPs blocked due to suspicious activity" />
              {blockedIps.length === 0 ? (
                <p className="text-sm text-slate-400 text-center py-6">No IPs currently blocked 🎉</p>
              ) : (
                <div className="space-y-2">
                  {blockedIps.map(b => (
                    <div key={b.ip} className="flex items-center justify-between py-2 border-b border-white/25 last:border-0">
                      <div>
                        <p className="text-sm font-mono font-semibold text-slate-900">{b.ip}</p>
                        <p className="text-xs text-slate-400">Unblocks in {Math.ceil(b.remaining_seconds / 60)} minutes</p>
                      </div>
                      <Button variant="ghost" size="sm" onClick={() => handleUnblock(b.ip)}>Unblock</Button>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card>
              <CardHeader title="Failed Login Attempts (24h)" subtitle="IPs with repeated failed logins" />
              {failedLogins.length === 0 ? (
                <p className="text-sm text-slate-400 text-center py-6">No failed login attempts 🎉</p>
              ) : (
                <div className="space-y-3">
                  {failedLogins.map(f => (
                    <div key={f.ip} className="bg-white/30 backdrop-blur-xl rounded-2xl border border-white/30 p-3 border border-white/25">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-mono font-semibold text-slate-900">{f.ip}</p>
                        <Badge variant={f.attempts >= 5 ? 'danger' : f.attempts >= 3 ? 'warning' : 'info'}>
                          {f.attempts} attempts
                        </Badge>
                      </div>
                      <p className="text-xs text-slate-500 mt-1">
                        Targeting: {f.emails_targeted.join(', ')}
                      </p>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Last: {new Date(f.last_attempt).toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        )}

        {/* Audit Trail Tab */}
        {activeTab === 'audit' && (
          <Card padding={false}>
            <div className="px-6 py-4 border-b border-white/40">
              <h3 className="text-base font-semibold text-slate-900">Security Audit Trail (24h)</h3>
              <p className="text-sm text-slate-500 mt-0.5">{auditEvents.length} events</p>
            </div>
            {auditEvents.length === 0 ? (
              <p className="text-sm text-slate-400 text-center py-8">No security events in the last 24 hours</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/40">
                      <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase">Time</th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase">User</th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase">Action</th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase">IP</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/25">
                    {auditEvents.slice(0, 100).map(e => (
                      <tr key={e.id} className="hover:bg-white/40">
                        <td className="px-6 py-3 text-slate-500 tabular-nums text-xs">
                          {new Date(e.created_at).toLocaleString()}
                        </td>
                        <td className="px-6 py-3 font-medium text-slate-900">{e.actor_email || 'System'}</td>
                        <td className="px-6 py-3">
                          <Badge variant={
                            e.action.includes('failed') ? 'danger' :
                            e.action.includes('login') ? 'success' :
                            e.action.includes('password') ? 'warning' : 'info'
                          }>
                            {e.action}
                          </Badge>
                        </td>
                        <td className="px-6 py-3 text-xs font-mono text-slate-500">{e.ip_address || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        )}

        {/* Security Features */}
        <div className="mt-8 pt-6 border-t border-white/40">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Active Security Features</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
            {[
              { name: 'JWT Auth', desc: 'Access + Refresh tokens', status: 'active' },
              { name: 'MFA (TOTP)', desc: 'Two-factor authentication', status: 'active' },
              { name: 'Rate Limiting', desc: '2000 req/min per IP', status: 'active' },
              { name: 'Brute Force Protection', desc: '5 attempts → 15min lock', status: 'active' },
              { name: 'IP Blocking', desc: 'Auto-block malicious IPs', status: 'active' },
              { name: 'Security Headers', desc: 'CSP, HSTS, X-Frame', status: 'active' },
              { name: 'Audit Logging', desc: 'All actions tracked', status: 'active' },
              { name: 'Input Sanitization', desc: 'XSS & SQLi prevention', status: 'active' },
              { name: 'Token Revocation', desc: 'Logout blacklists token', status: 'active' },
              { name: 'Password Policy', desc: 'Uppercase + special chars', status: 'active' },
              { name: 'RBAC', desc: 'Role + portfolio-level', status: 'active' },
              { name: 'Request Tracking', desc: 'X-Request-ID on all calls', status: 'active' },
            ].map(f => (
              <div key={f.name} className="bg-white/30 backdrop-blur-xl rounded-2xl border border-white/30 p-3 border border-white/25">
                <div className="flex items-center gap-1.5 mb-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  <p className="text-xs font-semibold text-slate-700">{f.name}</p>
                </div>
                <p className="text-[10px] text-slate-400">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
