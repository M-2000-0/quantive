import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { affiliateApi, type AffiliateDashboard, type AffiliateLink } from '../api/affiliate';
import { centsToUsd } from '../lib/money';

export default function AffiliateDashboardPage() {
  const [data, setData] = useState<AffiliateDashboard | null>(null);
  const [link, setLink] = useState<AffiliateLink | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [joining, setJoining] = useState(false);
  const [joinEmail, setJoinEmail] = useState('');
  const [copied, setCopied] = useState(false);
  const [tab, setTab] = useState<'overview' | 'referrals' | 'commissions'>('overview');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [dash, lnk] = await Promise.all([
        affiliateApi.getDashboard().catch(() => null),
        affiliateApi.getReferralLink().catch(() => null),
      ]);
      setData(dash);
      setLink(lnk);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load affiliate data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleJoin() {
    setJoining(true);
    setError('');
    try {
      await affiliateApi.join(joinEmail);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to join affiliate program');
    } finally {
      setJoining(false);
    }
  }

  function copyLink() {
    if (!link) return;
    const url = `${window.location.origin}${link.referral_link}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  if (loading && !data) return <div className="qp-card">Loading affiliate dashboard…</div>;

  if (!data) {
    return (
      <div style={{ display: 'grid', gap: 12 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <h1 style={{ margin: 0 }}>Affiliate Program</h1>
          <Link to="/qubo/workspace" className="qp-btn secondary" style={{ textDecoration: 'none' }}>← Qubo Tax</Link>
        </div>
        {error && <div className="qp-card" style={{ borderColor: '#f87171' }}>{error}</div>}
        <section className="qp-card">
          <h2>Join the Qubo Tax Affiliate Program</h2>
          <p className="qp-muted" style={{ fontSize: 13, marginBottom: 12 }}>
            Earn recurring commissions by referring businesses to Qubo Tax. Get 20% of each referred user's subscription payment, every billing period.
          </p>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <input
              type="email"
              placeholder="Payout email (optional)"
              value={joinEmail}
              onChange={(e) => setJoinEmail(e.target.value)}
              className="qp-input"
              style={{ maxWidth: 300 }}
            />
            <button className="qp-btn" onClick={() => void handleJoin()} disabled={joining}>
              {joining ? 'Joining…' : 'Join Affiliate Program →'}
            </button>
          </div>
          <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
            <div className="qp-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 750 }}>20%</div>
              <div className="qp-muted" style={{ fontSize: 12 }}>Recurring commission</div>
            </div>
            <div className="qp-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 750 }}>30 days</div>
              <div className="qp-muted" style={{ fontSize: 12 }}>Cookie duration</div>
            </div>
            <div className="qp-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 750 }}>Manual</div>
              <div className="qp-muted" style={{ fontSize: 12 }}>Payout method</div>
            </div>
          </div>
        </section>
      </div>
    );
  }

  const { affiliate, stats } = data;

  return (
    <div style={{ display: 'grid', gap: 12 }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <h1 style={{ margin: 0 }}>Affiliate Dashboard</h1>
        <span className="badge">{affiliate.referral_code}</span>
        <span className="badge">{(affiliate.commission_rate * 100).toFixed(0)}% commission</span>
        <span style={{ flex: 1 }} />
        <Link to="/qubo/workspace" className="qp-btn secondary" style={{ textDecoration: 'none' }}>← Qubo Tax</Link>
      </div>

      {error && <div className="qp-card" style={{ borderColor: '#f87171' }}>{error}</div>}

      {/* Referral Link */}
      <section className="qp-card">
        <h2>Your Referral Link</h2>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <code style={{ flex: 1, padding: '8px 12px', background: '#f3f4f6', borderRadius: 6, fontSize: 13 }}>
            {window.location.origin}{link?.referral_link ?? `/qubo/workspace?ref=${affiliate.referral_code}`}
          </code>
          <button className="qp-btn" onClick={copyLink}>
            {copied ? 'Copied!' : 'Copy Link'}
          </button>
        </div>
        {link && (
          <p className="qp-muted" style={{ fontSize: 12, marginTop: 8 }}>{link.share_text}</p>
        )}
      </section>

      {/* Stats Cards */}
      <section aria-label="Stats" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12 }}>
        <div className="qp-card">
          <span className="badge">Clicks</span>
          <div style={{ fontSize: 28, fontWeight: 750, marginTop: 8 }}>{stats.total_clicks}</div>
        </div>
        <div className="qp-card">
          <span className="badge">Referrals</span>
          <div style={{ fontSize: 28, fontWeight: 750, marginTop: 8 }}>{stats.total_referrals}</div>
        </div>
        <div className="qp-card">
          <span className="badge">Converted</span>
          <div style={{ fontSize: 28, fontWeight: 750, marginTop: 8 }}>{stats.referrals_by_status.converted ?? 0}</div>
        </div>
        <div className="qp-card">
          <span className="badge">Total Earned</span>
          <div style={{ fontSize: 28, fontWeight: 750, marginTop: 8 }}>{centsToUsd(stats.total_commission_cents)}</div>
        </div>
        <div className="qp-card">
          <span className="badge">Paid</span>
          <div style={{ fontSize: 28, fontWeight: 750, marginTop: 8 }}>{centsToUsd(stats.paid_commission_cents)}</div>
        </div>
        <div className="qp-card">
          <span className="badge">Pending</span>
          <div style={{ fontSize: 28, fontWeight: 750, marginTop: 8 }}>{centsToUsd(stats.pending_commission_cents)}</div>
        </div>
      </section>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8 }}>
        {(['overview', 'referrals', 'commissions'] as const).map((t) => (
          <button
            key={t}
            type="button"
            className={`qp-btn ${tab === t ? '' : 'secondary'}`}
            onClick={() => setTab(t)}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Referrals Tab */}
      {tab === 'referrals' && (
        <section className="qp-card">
          <h2>Referrals</h2>
          {data.referrals.length === 0 ? (
            <p className="qp-muted">No referrals yet. Share your referral link to get started!</p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                    <th style={{ textAlign: 'left', padding: '8px 4px' }}>Status</th>
                    <th style={{ textAlign: 'left', padding: '8px 4px' }}>Code</th>
                    <th style={{ textAlign: 'left', padding: '8px 4px' }}>Joined</th>
                    <th style={{ textAlign: 'left', padding: '8px 4px' }}>Converted</th>
                  </tr>
                </thead>
                <tbody>
                  {data.referrals.map((r) => (
                    <tr key={r.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                      <td style={{ padding: '8px 4px' }}>
                        <span className="badge" style={{
                          color: r.status === 'converted' ? '#16a34a' : r.status === 'registered' ? '#2563eb' : '#9ca3af',
                        }}>
                          {r.status}
                        </span>
                      </td>
                      <td style={{ padding: '8px 4px', fontFamily: 'monospace' }}>{r.referral_code}</td>
                      <td style={{ padding: '8px 4px' }}>{r.created_at ? new Date(r.created_at).toLocaleDateString() : '—'}</td>
                      <td style={{ padding: '8px 4px' }}>{r.converted_at ? new Date(r.converted_at).toLocaleDateString() : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {/* Commissions Tab */}
      {tab === 'commissions' && (
        <section className="qp-card">
          <h2>Commissions</h2>
          {data.commissions.length === 0 ? (
            <p className="qp-muted">No commissions yet. Commissions are earned when referred users pay for Qubo Tax.</p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                    <th style={{ textAlign: 'left', padding: '8px 4px' }}>Period</th>
                    <th style={{ textAlign: 'left', padding: '8px 4px' }}>Subscription</th>
                    <th style={{ textAlign: 'left', padding: '8px 4px' }}>Rate</th>
                    <th style={{ textAlign: 'left', padding: '8px 4px' }}>Commission</th>
                    <th style={{ textAlign: 'left', padding: '8px 4px' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.commissions.map((c) => (
                    <tr key={c.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                      <td style={{ padding: '8px 4px' }}>{c.billing_period}</td>
                      <td style={{ padding: '8px 4px' }}>{centsToUsd(c.subscription_amount_cents)}</td>
                      <td style={{ padding: '8px 4px' }}>{(c.commission_rate * 100).toFixed(0)}%</td>
                      <td style={{ padding: '8px 4px', fontWeight: 650 }}>{centsToUsd(c.commission_amount_cents)}</td>
                      <td style={{ padding: '8px 4px' }}>
                        <span className="badge" style={{
                          color: c.status === 'paid' ? '#16a34a' : c.status === 'approved' ? '#2563eb' : c.status === 'pending' ? '#f59e0b' : '#9ca3af',
                        }}>
                          {c.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {/* How it works */}
      {tab === 'overview' && (
        <section className="qp-card">
          <h2>How It Works</h2>
          <div style={{ display: 'grid', gap: 12, marginTop: 8 }}>
            {[
              { step: 1, title: 'Share your link', desc: 'Send your referral link to businesses who could benefit from Qubo Tax.' },
              { step: 2, title: 'They sign up', desc: 'When they click your link, a 30-day cookie tracks their visit. If they register, they\'re linked to you.' },
              { step: 3, title: 'They subscribe', desc: 'When the referred user pays for Qubo Tax, a commission is automatically created at your rate.' },
              { step: 4, title: 'Get paid', desc: 'Commissions are approved and paid manually. Contact us to arrange your payout.' },
            ].map(({ step, title, desc }) => (
              <div key={step} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#4D8DFF', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 14, flexShrink: 0 }}>
                  {step}
                </div>
                <div>
                  <div style={{ fontWeight: 650 }}>{title}</div>
                  <div className="qp-muted" style={{ fontSize: 13 }}>{desc}</div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
