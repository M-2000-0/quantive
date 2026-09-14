import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';
import type { Portfolio } from '../types';

export default function PortfoliosPage() {
  const navigate = useNavigate();
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [search, setSearch] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.portfolios.list({ page_size: 100, search: search || undefined });
      setPortfolios(res.data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load portfolios');
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    const t = setTimeout(() => void load(), search ? 300 : 0);
    return () => clearTimeout(t);
  }, [load, search]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setError('');
    try {
      const created = await api.portfolios.create({ name: name.trim(), description: description.trim() });
      setName('');
      setDescription('');
      navigate(`/dashboard/portfolios/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create failed');
    } finally {
      setCreating(false);
    }
  }

  async function handleSeedDemo() {
    setSeeding(true);
    setError('');
    try {
      const demo = await api.firstRun.createDemoPortfolio();
      navigate(`/dashboard/portfolios/${demo.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Demo seed failed');
    } finally {
      setSeeding(false);
    }
  }

  async function handleDelete(id: string, portfolioName: string) {
    if (!window.confirm(`Delete portfolio "${portfolioName}" and all its instruments?`)) return;
    setError('');
    try {
      await api.portfolios.delete(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    }
  }

  return (
    <div style={{ display: 'grid', gap: 12, maxWidth: 860 }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <h1 style={{ margin: 0 }}>Portfolios</h1>
        <span style={{ flex: 1 }} />
        <input
          type="search"
          aria-label="Search portfolios"
          placeholder="Search…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #e5e7eb' }}
        />
      </div>

      {error && <div className="qp-card" style={{ borderColor: '#f87171' }}>{error}</div>}

      <form onSubmit={(e) => void handleCreate(e)} className="qp-card" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'end' }}>
        <label style={{ flex: '1 1 200px' }}>Name
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Sovereign Bond Portfolio" style={{ display: 'block', width: '100%', marginTop: 4, padding: '8px 12px', borderRadius: 8, border: '1px solid #e5e7eb' }} />
        </label>
        <label style={{ flex: '2 1 280px' }}>Description
          <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="USD + EUR benchmark sleeve" style={{ display: 'block', width: '100%', marginTop: 4, padding: '8px 12px', borderRadius: 8, border: '1px solid #e5e7eb' }} />
        </label>
        <button type="submit" className="qp-btn" disabled={creating || !name.trim()}>
          {creating ? 'Creating…' : 'Create portfolio'}
        </button>
      </form>

      <section aria-label="Portfolio list" className="qp-card">
        {loading && <p className="qp-muted">Loading portfolios…</p>}
        {!loading && portfolios.length === 0 && (
          <div style={{ textAlign: 'center', padding: '28px 16px' }}>
            <h2 style={{ margin: '0 0 8px' }}>No portfolios yet</h2>
            <p className="qp-muted" style={{ maxWidth: 480, margin: '0 auto 16px' }}>
              Portfolios are step one of the loop: add instruments, run an optimization,
              review risk. Create one above — or load a demo portfolio instantly.
            </p>
            <button className="qp-btn" onClick={() => void handleSeedDemo()} disabled={seeding}>
              {seeding ? 'Loading demo…' : 'Load demo portfolio →'}
            </button>
          </div>
        )}
        {portfolios.map((p) => (
          <div key={p.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, padding: '10px 0', borderBottom: '1px solid #f3f4f6' }}>
            <div>
              <Link to={`/dashboard/portfolios/${p.id}`} style={{ fontWeight: 650 }}>{p.name}</Link>
              {p.description && <div className="qp-muted" style={{ fontSize: 12 }}>{p.description}</div>}
            </div>
            <button
              type="button"
              className="qp-btn secondary"
              onClick={() => void handleDelete(p.id, p.name)}
            >
              Delete
            </button>
          </div>
        ))}
      </section>
    </div>
  );
}
