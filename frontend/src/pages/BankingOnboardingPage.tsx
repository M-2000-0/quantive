import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, type BankingProfile } from '../api';

const STATUS_COPY: Record<string, string> = {
  draft: 'Draft — complete the form and submit for KYB review.',
  pending: 'Pending — with the partner bank for KYB review. Legitimate reviews ask for documents; that is the system working.',
  verified: 'Verified — your business is approved. Profile is locked; contact support to amend.',
  rejected: 'Rejected — see notes, correct the details and resubmit.',
};

export default function BankingOnboardingPage() {
  const [profile, setProfile] = useState<BankingProfile | null>(null);
  const [status, setStatus] = useState('draft');
  const [form, setForm] = useState({ legal_name: '', dba: '', entity_type: '', country: 'US', industry: '', tax_id_last4: '' });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.banking.profile();
      setProfile(res.profile);
      setStatus(res.kyb_status);
      if (res.profile) {
        setForm({
          legal_name: res.profile.legal_name,
          dba: res.profile.dba,
          entity_type: res.profile.entity_type,
          country: res.profile.country,
          industry: res.profile.industry,
          tax_id_last4: res.profile.tax_id_last4,
        });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load profile');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function set<K extends keyof typeof form>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setNotice('');
    setSaving(true);
    try {
      const saved = await api.banking.saveProfile(form);
      setProfile(saved);
      setStatus(saved.kyb_status);
      setNotice('Profile saved.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  }

  async function handleSubmit() {
    setError('');
    setNotice('');
    try {
      const submitted = await api.banking.submitProfile();
      setProfile(submitted);
      setStatus(submitted.kyb_status);
      setNotice('Submitted for KYB review.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Submit failed');
    }
  }

  if (loading) return <div className="qp-card">Loading onboarding…</div>;
  const locked = status === 'verified';

  return (
    <div style={{ display: 'grid', gap: 12, maxWidth: 640 }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <h1 style={{ margin: 0 }}>Business onboarding</h1>
        <span className="badge">{status}</span>
        <span style={{ flex: 1 }} />
        <Link to="/banking/app" className="qp-btn secondary" style={{ textDecoration: 'none' }}>← Dashboard</Link>
      </div>

      <div className="qp-card"><p className="qp-muted" style={{ margin: 0 }}>{STATUS_COPY[status] ?? status}</p></div>
      {profile?.kyb_notes && <div className="qp-card">Reviewer notes: {profile.kyb_notes}</div>}
      {error && <div className="qp-card" style={{ borderColor: '#f87171' }}>{error}</div>}
      {notice && <div className="qp-card" style={{ borderColor: '#34d399' }}>{notice}</div>}

      <form onSubmit={(e) => void handleSave(e)} className="qp-card" style={{ display: 'grid', gap: 10 }}>
        <label>Legal business name
          <input value={form.legal_name} onChange={(e) => set('legal_name', e.target.value)} disabled={locked} style={{ display: 'block', width: '100%', marginTop: 4 }} />
        </label>
        <label>DBA (optional)
          <input value={form.dba} onChange={(e) => set('dba', e.target.value)} disabled={locked} style={{ display: 'block', width: '100%', marginTop: 4 }} />
        </label>
        <label>Entity type
          <select value={form.entity_type} onChange={(e) => set('entity_type', e.target.value)} disabled={locked} style={{ display: 'block', width: '100%', marginTop: 4 }}>
            <option value="">Select…</option>
            <option value="llc">LLC</option>
            <option value="corporation">Corporation</option>
            <option value="partnership">Partnership</option>
            <option value="sole_proprietorship">Sole proprietorship</option>
          </select>
        </label>
        <label>Country
          <input value={form.country} onChange={(e) => set('country', e.target.value.toUpperCase())} maxLength={2} disabled={locked} style={{ display: 'block', width: '100%', marginTop: 4 }} />
        </label>
        <label>Industry
          <input value={form.industry} onChange={(e) => set('industry', e.target.value)} disabled={locked} style={{ display: 'block', width: '100%', marginTop: 4 }} />
        </label>
        <label>Tax ID (last 4)
          <input value={form.tax_id_last4} onChange={(e) => set('tax_id_last4', e.target.value.replace(/\D/g, '').slice(0, 4))} inputMode="numeric" disabled={locked} style={{ display: 'block', width: '100%', marginTop: 4 }} />
        </label>
        {!locked && (
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="submit" className="qp-btn secondary" disabled={saving}>{saving ? 'Saving…' : 'Save draft'}</button>
            <button type="button" className="qp-btn" onClick={() => void handleSubmit()}>Submit for KYB review →</button>
          </div>
        )}
      </form>
      <p className="qp-muted" style={{ fontSize: 12 }}>
        Identity verification, sanctions screening and transaction monitoring apply via our licensed banking partner.
        We never promise "no regulation, no reporting" — holding money means following rules.
      </p>
    </div>
  );
}
