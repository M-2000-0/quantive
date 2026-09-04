import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';

export default function NewOptimizationPage() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.optimizations.create({ name });
      navigate('/optimizations');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create optimization');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ maxWidth: 560 }}>
      <h1>New optimization</h1>
      <p style={{ color: '#6b7280', marginBottom: 16 }}>
        Name your run to queue it. Results appear under <Link to="/optimizations">Optimizations</Link>.
      </p>
      <form onSubmit={handleSubmit} className="panel">
        <label htmlFor="opt-name">Run name</label>
        <input
          id="opt-name"
          className="glass-input"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Q1 refinancing pass"
          required
        />
        {error && (
          <p role="alert" style={{ color: '#dc2626', marginTop: 8 }}>
            {error}
          </p>
        )}
        <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
          <button type="submit" className="primary-button" disabled={saving}>
            {saving ? 'Queueing...' : 'Queue optimization'}
          </button>
          <Link to="/optimizations" className="soft-button">
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
