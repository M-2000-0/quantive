import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import AppShell from '../components/layout/AppShell';
import { Button, Card, CardHeader, Badge } from '../components/ui';
import { api } from '../api';
import { MOCK_PORTFOLIOS } from '../api/mock';

type ImportMethod = 'upload' | 'demo' | 'manual';
type Step = 'method' | 'validate' | 'configure';

interface ValidationCheck {
  label: string;
  passed: boolean;
  detail?: string;
}

interface ParsedRow {
  name: string;
  type: string;
  currency: string;
  principal: number;
  coupon: number;
  maturity: string;
  spread: number;
  callable: boolean;
}

function parseCSV(text: string): { rows: ParsedRow[]; errors: string[] } {
  const lines = text.trim().split('\n');
  if (lines.length < 2) return { rows: [], errors: ['File is empty or has no data rows'] };
  const headers = lines[0].split(',').map((h) => h.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_'));
  const requiredFields = ['name', 'currency', 'principal'];
  const missing = requiredFields.filter((f) => !headers.some((h) => h.includes(f)));
  if (missing.length > 0) return { rows: [], errors: [`Missing required columns: ${missing.join(', ')}`] };
  const rows: ParsedRow[] = [];
  const errors: string[] = [];
  for (let i = 1; i < lines.length; i++) {
    const vals = lines[i].split(',').map((v) => v.trim());
    if (vals.length < headers.length) { errors.push(`Row ${i + 1}: Insufficient columns`); continue; }
    const get = (field: string) => { const idx = headers.findIndex((h) => h.includes(field)); return idx >= 0 ? vals[idx] : ''; };
    const name = get('name');
    const currency = get('currency').toUpperCase();
    const principalStr = get('principal') || get('principal_outstanding') || '0';
    const principal = parseFloat(principalStr.replace(/[^0-9.]/g, ''));
    if (!name) { errors.push(`Row ${i + 1}: Missing instrument name`); continue; }
    if (!currency || currency.length !== 3) { errors.push(`Row ${i + 1}: Invalid currency code "${currency}"`); continue; }
    if (isNaN(principal) || principal <= 0) { errors.push(`Row ${i + 1}: Invalid principal amount`); continue; }
    rows.push({
      name,
      type: get('type') || get('instrument_type') || 'bond',
      currency,
      principal,
      coupon: parseFloat(get('coupon') || get('coupon_rate') || '0') || 0,
      maturity: get('maturity') || get('maturity_date') || '',
      spread: parseFloat(get('spread') || get('spread_bps') || '0') || 0,
      callable: (get('callable') || get('is_callable') || '').toLowerCase() === 'true',
    });
  }
  return { rows, errors };
}

function validateData(rows: ParsedRow[]): ValidationCheck[] {
  const checks: ValidationCheck[] = [];
  checks.push({ label: `${rows.length} instruments detected`, passed: rows.length > 0 });
  const validCurrencies = rows.every((r) => /^[A-Z]{3}$/.test(r.currency));
  checks.push({ label: 'Currency data valid', passed: validCurrencies, detail: validCurrencies ? undefined : 'Some currency codes are invalid' });
  const validDates = rows.filter((r) => r.maturity).every((r) => !isNaN(Date.parse(r.maturity)));
  checks.push({ label: 'Maturity dates valid', passed: validDates, detail: validDates ? undefined : 'Some maturity dates could not be parsed' });
  const uniqueNames = new Set(rows.map((r) => r.name));
  const noDuplicates = uniqueNames.size === rows.length;
  checks.push({ label: 'No duplicate records', passed: noDuplicates, detail: noDuplicates ? undefined : `Found ${rows.length - uniqueNames.size} duplicate names` });
  checks.push({ label: 'Portfolio ready', passed: rows.length > 0 && validCurrencies && noDuplicates });
  return checks;
}

export default function NewPortfolioPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState<Step>('method');
  const [method, setMethod] = useState<ImportMethod | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [parsedRows, setParsedRows] = useState<ParsedRow[]>([]);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [validationChecks, setValidationChecks] = useState<ValidationCheck[]>([]);
  const [fileName, setFileName] = useState('');
  const [previewRows, setPreviewRows] = useState<string[][]>([]);

  const handleFile = useCallback((file: File) => {
    setError('');
    setFileName(file.name);
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext !== 'csv' && ext !== 'xlsx' && ext !== 'xls') {
      setError('Unsupported file format. Please upload CSV, XLSX, or XLS.');
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      if (!text) { setError('Could not read file.'); return; }
      const lines = text.trim().split('\n');
      const headerLine = lines[0].split(',').map((h) => h.trim());
      const dataLines = lines.slice(1, 6).map((l) => l.split(',').map((v) => v.trim()));
      setPreviewRows([headerLine, ...dataLines]);
      const { rows, errors } = parseCSV(text);
      if (errors.length > 0 && rows.length === 0) { setValidationErrors(errors); return; }
      setParsedRows(rows);
      setValidationErrors(errors);
      setValidationChecks(validateData(rows));
      setStep('validate');
    };
    reader.onerror = () => setError('Failed to read file.');
    reader.readAsText(file);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleMethodSelect = (m: ImportMethod) => {
    setMethod(m);
    if (m === 'demo') {
      const demo = MOCK_PORTFOLIOS[0];
      setName(demo.name);
      setDescription(demo.description);
      const rows: ParsedRow[] = demo.instruments.map((i) => ({
        name: i.name, type: i.instrument_type, currency: i.currency,
        principal: i.principal_outstanding, coupon: i.coupon_rate,
        maturity: i.maturity_date, spread: i.spread_bps, callable: i.is_callable,
      }));
      setParsedRows(rows);
      setValidationErrors([]);
      setValidationChecks(validateData(rows));
      setStep('validate');
    } else if (m === 'manual') {
      setStep('configure');
    }
  };

  const handleProceedFromValidation = () => {
    const failed = validationChecks.filter((c) => !c.passed && c.label !== 'Portfolio ready');
    if (failed.length > 0) return;
    setStep('configure');
  };

  const handleSubmit = async () => {
    if (!name.trim()) { setError('Portfolio name is required.'); return; }
    setError('');
    setLoading(true);
    try {
      if (method === 'upload' && fileName) {
        const headerLine = previewRows[0]?.join(',') || 'name,type,currency,principal,coupon,maturity,spread,callable';
        const dataLines = parsedRows.map((r) =>
          [r.name, r.type, r.currency, String(r.principal), String(r.coupon), r.maturity, String(r.spread), String(r.callable)].join(',')
        );
        const blob = new Blob([headerLine + '\n' + dataLines.join('\n')], { type: 'text/csv' });
        const file = new File([blob], `${name.replace(/\s+/g, '_')}.csv`, { type: 'text/csv' });
        const formData = new FormData();
        formData.append('file', file);
        formData.append('name', name);
        formData.append('description', description);
        const portfolio = await api.portfolios.upload(formData);
        navigate(`/portfolios/${portfolio.id}`);
      } else {
        const instruments = parsedRows.map((r) => ({
          name: r.name, instrument_type: r.type, currency: r.currency,
          principal_outstanding: r.principal, coupon_rate: r.coupon,
          maturity_date: r.maturity, spread_bps: r.spread,
          is_callable: r.callable, issue_date: new Date().toISOString().split('T')[0],
        }));
        const portfolio = await api.portfolios.create({ name, description, instruments });
        navigate(`/portfolios/${portfolio.id}`);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to create portfolio');
    } finally {
      setLoading(false);
    }
  };

  const StepIndicator = ({ current }: { current: Step }) => {
    const steps: { key: Step; label: string; num: number }[] = [
      { key: 'method', label: 'Import Method', num: 1 },
      { key: 'validate', label: 'Validation', num: 2 },
      { key: 'configure', label: 'Configure', num: 3 },
    ];
    return (
      <div className="flex items-center gap-3 mb-8">
        {steps.map((s, i) => {
          const isComplete = steps.findIndex((x) => x.key === current) > i;
          const isCurrent = s.key === current;
          return (
            <div key={s.key} className="flex items-center gap-3">
              {i > 0 && <div className={`w-8 h-px ${isComplete ? 'bg-blue-600' : 'bg-slate-200'}`} />}
              <div className="flex items-center gap-2">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${isComplete || isCurrent ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500'}`}>
                  {isComplete ? (
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  ) : s.num}
                </div>
                <span className={`text-sm font-medium ${isCurrent ? 'text-slate-900' : 'text-slate-400'}`}>{s.label}</span>
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <AppShell>
      <div className="px-8 py-6 max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">New Portfolio</h1>
          <p className="mt-1 text-sm text-slate-500">Import or create a new debt portfolio for analysis</p>
        </div>
        <StepIndicator current={step} />

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">{error}</div>
        )}

        {step === 'method' && (
          <div className="space-y-4">
            <div
              onClick={() => handleMethodSelect('upload')}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all ${dragOver ? 'border-blue-400 bg-blue-50/50' : 'border-slate-300 hover:border-blue-400 hover:bg-slate-50'}`}
            >
              <div className="flex flex-col items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-blue-50 flex items-center justify-center">
                  <svg className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-900">Upload CSV / Excel file</p>
                  <p className="text-xs text-slate-500 mt-1">Drag and drop or click to browse. Supports CSV, XLSX, XLS.</p>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  {['.csv', '.xlsx', '.xls'].map((ext) => (
                    <span key={ext} className="px-2 py-0.5 text-xs font-medium bg-slate-100 text-slate-600 rounded">{ext}</span>
                  ))}
                </div>
              </div>
              <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls" className="hidden"
                onChange={(e) => { const file = e.target.files?.[0]; if (file) handleFile(file); }} />
            </div>

            <button onClick={() => handleMethodSelect('demo')} className="w-full border border-slate-200 rounded-lg p-5 text-left hover:bg-slate-50 hover:border-slate-300 transition-all group">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-emerald-50 flex items-center justify-center group-hover:bg-emerald-100 transition-colors">
                  <svg className="h-5 w-5 text-emerald-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.212-1.687 4.125-8.25 4.125s-8.25-1.913-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.212-1.687 4.125-8.25 4.125s-8.25-1.913-8.25-4.125" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-900">Use demonstration dataset</p>
                  <p className="text-xs text-slate-500 mt-0.5">Load a pre-built sovereign debt portfolio with 10 instruments across 4 currencies</p>
                </div>
              </div>
            </button>

            <button onClick={() => handleMethodSelect('manual')} className="w-full border border-slate-200 rounded-lg p-5 text-left hover:bg-slate-50 hover:border-slate-300 transition-all group">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-violet-50 flex items-center justify-center group-hover:bg-violet-100 transition-colors">
                  <svg className="h-5 w-5 text-violet-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-900">Manual entry</p>
                  <p className="text-xs text-slate-500 mt-0.5">Create an empty portfolio and add instruments manually</p>
                </div>
              </div>
            </button>
          </div>
        )}

        {step === 'validate' && (
          <div className="space-y-6">
            <Card>
              <CardHeader
                title="Validation Results"
                subtitle={fileName ? `File: ${fileName}` : 'Demonstration dataset'}
                action={method === 'upload' ? (
                  <Button variant="ghost" size="sm" onClick={() => { setStep('method'); setFileName(''); setParsedRows([]); }}>Change file</Button>
                ) : undefined}
              />
              {previewRows.length > 0 && (
                <div className="mb-6">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Preview (first {previewRows.length - 1} rows)</p>
                  <div className="overflow-x-auto border border-slate-200 rounded-md">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="bg-slate-50">
                          {previewRows[0]?.map((h, i) => (
                            <th key={i} className="px-3 py-2 text-left font-semibold text-slate-600 whitespace-nowrap">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {previewRows.slice(1).map((row, ri) => (
                          <tr key={ri} className="hover:bg-slate-50/50">
                            {row.map((cell, ci) => (
                              <td key={ci} className="px-3 py-2 text-slate-700 whitespace-nowrap">{cell}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
              <div className="space-y-2.5">
                {validationChecks.map((check, i) => (
                  <div key={i} className="flex items-center gap-3">
                    {check.passed ? (
                      <div className="w-5 h-5 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0">
                        <svg className="h-3 w-3 text-emerald-600" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                        </svg>
                      </div>
                    ) : (
                      <div className="w-5 h-5 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
                        <svg className="h-3 w-3 text-red-600" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </div>
                    )}
                    <span className={`text-sm ${check.passed ? 'text-slate-700' : 'text-red-600'}`}>
                      {check.passed ? '\u2713' : '\u2717'} {check.label}
                    </span>
                    {check.detail && <span className="text-xs text-slate-400 ml-1">&mdash; {check.detail}</span>}
                  </div>
                ))}
              </div>
              {validationErrors.length > 0 && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
                  <p className="text-xs font-semibold text-red-700 mb-1">Errors</p>
                  <ul className="space-y-1">
                    {validationErrors.slice(0, 10).map((err, i) => (
                      <li key={i} className="text-xs text-red-600">{err}</li>
                    ))}
                    {validationErrors.length > 10 && (
                      <li className="text-xs text-red-500">...and {validationErrors.length - 10} more</li>
                    )}
                  </ul>
                </div>
              )}
            </Card>
            <div className="flex items-center justify-between">
              <Button variant="ghost" onClick={() => { setStep('method'); setFileName(''); setParsedRows([]); }}>Back</Button>
              <Button variant="primary" onClick={handleProceedFromValidation}
                disabled={validationChecks.some((c) => !c.passed && c.label !== 'Portfolio ready')}>
                Continue to Configuration
              </Button>
            </div>
          </div>
        )}

        {step === 'configure' && (
          <div className="space-y-6">
            <Card>
              <CardHeader title="Portfolio Configuration" subtitle="Define portfolio metadata and review detected instruments" />
              <div className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Portfolio Name</label>
                  <input type="text" value={name} onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Sovereign Debt Portfolio - FY2026"
                    className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Description</label>
                  <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3}
                    placeholder="Brief description of the portfolio purpose and scope..."
                    className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none" />
                </div>
              </div>
            </Card>

            {parsedRows.length > 0 && (
              <Card>
                <CardHeader title="Detected Instruments" subtitle={`${parsedRows.length} instruments ready for import`}
                  action={<div className="flex gap-1.5">{Array.from(new Set(parsedRows.map((r) => r.currency))).map((c) => (
                    <Badge key={c} variant="info" size="sm">{c}</Badge>
                  ))}</div>} />
                <div className="overflow-x-auto border border-slate-200 rounded-md max-h-80 overflow-y-auto">
                  <table className="w-full text-xs">
                    <thead className="sticky top-0 bg-white">
                      <tr className="border-b border-slate-200">
                        {['Name', 'Type', 'CCY', 'Principal', 'Coupon', 'Maturity', 'Spread', 'Callable'].map((h) => (
                          <th key={h} className={`px-3 py-2 font-semibold text-slate-500 ${['Principal', 'Coupon', 'Spread'].includes(h) ? 'text-right' : h === 'Callable' ? 'text-center' : 'text-left'}`}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50">
                      {parsedRows.map((row, i) => (
                        <tr key={i} className="hover:bg-slate-50/50">
                          <td className="px-3 py-2 text-slate-900 font-medium max-w-[200px] truncate">{row.name}</td>
                          <td className="px-3 py-2 text-slate-600 whitespace-nowrap">{row.type.replace(/_/g, ' ')}</td>
                          <td className="px-3 py-2"><Badge variant="info" size="sm">{row.currency}</Badge></td>
                          <td className="px-3 py-2 text-right text-slate-700">${row.principal.toLocaleString()}</td>
                          <td className="px-3 py-2 text-right text-slate-700">{(row.coupon * 100).toFixed(2)}%</td>
                          <td className="px-3 py-2 text-slate-600 whitespace-nowrap">{row.maturity || '—'}</td>
                          <td className="px-3 py-2 text-right text-slate-700">{row.spread} bps</td>
                          <td className="px-3 py-2 text-center">
                            {row.callable ? (
                              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">Yes</span>
                            ) : (
                              <span className="text-slate-400 text-xs">No</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}

            <div className="flex items-center justify-between">
              <Button variant="ghost" onClick={() => setStep(method === 'upload' ? 'validate' : 'method')}>Back</Button>
              <div className="flex gap-3">
                <Button variant="secondary" onClick={() => navigate('/')}>Cancel</Button>
                <Button variant="primary" loading={loading} onClick={handleSubmit}>Create Portfolio</Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
