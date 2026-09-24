import { useState, useCallback } from 'react';
import { Link } from 'react-router-dom';

interface ImportResult {
  status: string;
  records_imported: number;
  records_skipped: number;
  errors: string[];
  warnings: string[];
  import_id: string;
}

interface PFMSummary {
  total_budget_entries: number;
  total_revenue_records: number;
  total_expenditure_records: number;
  total_audit_findings: number;
  total_statements: number;
  total_ifmis_connections: number;
  latest_fiscal_year: number | null;
  budget_execution_rate: number;
  revenue_collection_rate: number;
  open_audit_findings: number;
  total_financial_impact: number;
}

const DATA_TYPES = [
  { key: 'budget', label: 'Budget Entries', icon: '📊', desc: 'Formulation, approval, execution data' },
  { key: 'revenue', label: 'Revenue Records', icon: '💰', desc: 'Tax, customs, grants, other income' },
  { key: 'expenditure', label: 'Expenditure Records', icon: '📤', desc: 'Procurement, payroll, transfers' },
  { key: 'audit', label: 'Audit Findings', icon: '🔍', desc: 'Internal, external, compliance audits' },
  { key: 'financial-statement', label: 'Financial Statements', icon: '📋', desc: 'Balance sheet, income, cash flow' },
] as const;

export default function PFMImportPage() {
  const [activeTab, setActiveTab] = useState<string>('upload');
  const [selectedType, setSelectedType] = useState<string>('budget');
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [summary, setSummary] = useState<PFMSummary | null>(null);
  const [fiscalYear, setFiscalYear] = useState<string>(new Date().getFullYear().toString());

  const fetchSummary = useCallback(async () => {
    try {
      const res = await fetch('/api/pfm/summary');
      if (res.ok) setSummary(await res.json());
    } catch {}
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);
    if (fiscalYear) formData.append('fiscal_year', fiscalYear);

    try {
      const csrfMatch = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
      const csrf = csrfMatch ? decodeURIComponent(csrfMatch[1]) : '';
      const res = await fetch(`/api/pfm/import/${selectedType}`, {
        method: 'POST',
        credentials: 'include',
        headers: { ...(csrf ? { 'X-CSRF-Token': csrf } : {}) },
        body: formData,
      });
      const data = await res.json();
      setResult(data);
      fetchSummary();
    } catch (err) {
      setResult({
        status: 'error',
        records_imported: 0,
        records_skipped: 0,
        errors: [`Upload failed: ${err}`],
        warnings: [],
        import_id: '',
      });
    } finally {
      setUploading(false);
    }
  };

  const downloadTemplate = async (type: string) => {
    try {
      const res = await fetch(`/api/pfm/templates/${type}`);
      const data = await res.json();
      const blob = new Blob([data.template], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = data.filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch {}
  };

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: 24 }}>
      <nav style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <Link to="/">← Home</Link>
        <Link to="/government">Government</Link>
        <Link to="/sovereign-mode">Sovereign Mode</Link>
      </nav>

      <h1 style={{ color: '#c8a951', marginBottom: 4 }}>PFM Data Import</h1>
      <p style={{ color: '#9ca3af', marginBottom: 24 }}>
        Import government financial management data — budgets, revenue, expenditure, audits, and statements.
      </p>

      {/* Summary Cards */}
      {summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 24 }}>
          {[
            { label: 'Budget Entries', value: summary.total_budget_entries, color: '#c8a951' },
            { label: 'Revenue Records', value: summary.total_revenue_records, color: '#10b981' },
            { label: 'Expenditure Records', value: summary.total_expenditure_records, color: '#3b82f6' },
            { label: 'Audit Findings', value: summary.total_audit_findings, color: '#ef4444' },
          ].map((card) => (
            <div key={card.label} style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 8, padding: 16 }}>
              <div style={{ color: '#6b7280', fontSize: 12, textTransform: 'uppercase' }}>{card.label}</div>
              <div style={{ color: card.color, fontSize: 24, fontWeight: 700 }}>{card.value.toLocaleString()}</div>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid #1f2937', paddingBottom: 8 }}>
        {['upload', 'data', 'templates'].map((tab) => (
          <button
            key={tab}
            onClick={() => { setActiveTab(tab); if (tab === 'data') fetchSummary(); }}
            style={{
              padding: '8px 16px',
              background: activeTab === tab ? '#c8a951' : 'transparent',
              color: activeTab === tab ? '#000' : '#9ca3af',
              border: 'none',
              borderRadius: 6,
              cursor: 'pointer',
              fontWeight: 600,
              textTransform: 'capitalize',
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Upload Tab */}
      {activeTab === 'upload' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 16 }}>Import Data</h3>

          {/* Data Type Selection */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8, marginBottom: 20 }}>
            {DATA_TYPES.map((dt) => (
              <button
                key={dt.key}
                onClick={() => setSelectedType(dt.key)}
                style={{
                  padding: 12,
                  background: selectedType === dt.key ? '#1a1d24' : '#0d0f13',
                  border: `1px solid ${selectedType === dt.key ? '#c8a951' : '#1f2937'}`,
                  borderRadius: 8,
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                <div style={{ fontSize: 20, marginBottom: 4 }}>{dt.icon}</div>
                <div style={{ color: '#e5e7eb', fontSize: 13, fontWeight: 600 }}>{dt.label}</div>
                <div style={{ color: '#6b7280', fontSize: 11 }}>{dt.desc}</div>
              </button>
            ))}
          </div>

          {/* Fiscal Year */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ color: '#9ca3af', fontSize: 13, display: 'block', marginBottom: 4 }}>Fiscal Year (optional)</label>
            <input
              type="number"
              value={fiscalYear}
              onChange={(e) => setFiscalYear(e.target.value)}
              style={{ background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 6, padding: '8px 12px', color: '#e5e7eb', width: 120 }}
            />
          </div>

          {/* File Upload */}
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <label
              style={{
                padding: '10px 20px',
                background: '#c8a951',
                color: '#000',
                borderRadius: 6,
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: 14,
              }}
            >
              {uploading ? 'Uploading...' : 'Choose CSV or Excel File'}
              <input
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={handleUpload}
                disabled={uploading}
                style={{ display: 'none' }}
              />
            </label>
            <button
              onClick={() => downloadTemplate(selectedType)}
              style={{ padding: '10px 16px', background: 'transparent', border: '1px solid #1f2937', borderRadius: 6, color: '#9ca3af', cursor: 'pointer' }}
            >
              Download Template
            </button>
          </div>

          {/* Result */}
          {result && (
            <div style={{
              marginTop: 20,
              padding: 16,
              background: result.status === 'success' ? '#052e16' : '#1c1917',
              border: `1px solid ${result.status === 'success' ? '#166534' : '#7f1d1d'}`,
              borderRadius: 8,
            }}>
              <div style={{ color: result.status === 'success' ? '#22c55e' : '#ef4444', fontWeight: 600, marginBottom: 8 }}>
                {result.status === 'success' ? 'Import Successful' : 'Import Issues'}
              </div>
              <div style={{ color: '#d1d5db', fontSize: 14 }}>
                {result.records_imported} records imported, {result.records_skipped} skipped
              </div>
              {result.errors.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  {result.errors.slice(0, 5).map((err, i) => (
                    <div key={i} style={{ color: '#fca5a5', fontSize: 13 }}>• {err}</div>
                  ))}
                  {result.errors.length > 5 && (
                    <div style={{ color: '#6b7280', fontSize: 13 }}>...and {result.errors.length - 5} more errors</div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Data Tab */}
      {activeTab === 'data' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 16 }}>Imported Data</h3>
          <p style={{ color: '#6b7280' }}>
            Data viewing and filtering coming soon. For now, data is stored in the database and accessible via the API endpoints.
          </p>
          <div style={{ marginTop: 16, display: 'grid', gap: 8 }}>
            {[
              { endpoint: '/api/pfm/budget', desc: 'Budget entries' },
              { endpoint: '/api/pfm/revenue', desc: 'Revenue records' },
              { endpoint: '/api/pfm/expenditure', desc: 'Expenditure records' },
              { endpoint: '/api/pfm/audit', desc: 'Audit findings' },
              { endpoint: '/api/pfm/summary', desc: 'PFM summary' },
            ].map((ep) => (
              <div key={ep.endpoint} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: '#0d0f13', borderRadius: 6 }}>
                <code style={{ color: '#c8a951', fontSize: 13 }}>{ep.endpoint}</code>
                <span style={{ color: '#6b7280', fontSize: 13 }}>{ep.desc}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Templates Tab */}
      {activeTab === 'templates' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 16 }}>CSV Templates</h3>
          <p style={{ color: '#9ca3af', marginBottom: 16 }}>
            Download pre-formatted CSV templates with sample data. Fill in your data and upload.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
            {DATA_TYPES.map((dt) => (
              <button
                key={dt.key}
                onClick={() => downloadTemplate(dt.key)}
                style={{
                  padding: 16,
                  background: '#0d0f13',
                  border: '1px solid #1f2937',
                  borderRadius: 8,
                  cursor: 'pointer',
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: 24, marginBottom: 8 }}>{dt.icon}</div>
                <div style={{ color: '#e5e7eb', fontSize: 13, fontWeight: 600 }}>{dt.label}</div>
                <div style={{ color: '#c8a951', fontSize: 12, marginTop: 4 }}>Download CSV</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* IFMIS Integration Section */}
      <div style={{ marginTop: 24, background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
        <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>IFMIS Integration</h3>
        <p style={{ color: '#9ca3af', marginBottom: 16 }}>
          Connect directly to your Integrated Financial Management Information System for automated data sync.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
          {[
            { name: 'IFMIS (Generic)', status: 'Coming Soon', desc: 'Standard IFMIS API connector' },
            { name: 'GIFMIS (Philippines)', status: 'Coming Soon', desc: 'Government Financial Management' },
            { name: 'IFMIS (Zambia)', status: 'Coming Soon', desc: 'Zambia Treasury system' },
          ].map((sys) => (
            <div key={sys.name} style={{ padding: 16, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8 }}>
              <div style={{ color: '#e5e7eb', fontWeight: 600, marginBottom: 4 }}>{sys.name}</div>
              <div style={{ color: '#6b7280', fontSize: 13, marginBottom: 8 }}>{sys.desc}</div>
              <div style={{ color: '#c8a951', fontSize: 12, fontWeight: 600 }}>{sys.status}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
