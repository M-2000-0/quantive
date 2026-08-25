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
  isin?: string;
  issue_date?: string;
}

interface RowError {
  rowIndex: number; // 1-based data row (excluding header)
  field?: string;
  message: string;
}

// ── Column mapping aliases ─────────────────────────────────────────────
const COLUMN_ALIASES: Record<string, string[]> = {
  name: ['name', 'instrument_name', 'title', 'description', 'instrument'],
  instrument_type: ['instrument_type', 'type', 'instrument', 'asset_type', 'security_type'],
  currency: ['currency', 'ccy', 'curr', 'currency_code', 'cur'],
  principal_outstanding: ['principal_outstanding', 'principal', 'notional', 'amount', 'face_value', 'principal_amount', 'outstanding', 'par'],
  coupon: ['coupon', 'coupon_rate', 'couponrate', 'rate', 'interest_rate', 'coupon_pct', 'coupon_percent'],
  maturity_date: ['maturity_date', 'maturity', 'maturitydate', 'maturity_dt', 'end_date', 'maturity_maturity', 'tenor'],
  spread: ['spread', 'spread_bps', 'spreadbps', 'bps', 'margin'],
  callable: ['callable', 'is_callable', 'call', 'callable_flag'],
  isin: ['isin', 'isin_code', 'isincode'],
  issue_date: ['issue_date', 'issue', 'start_date', 'issue_dt'],
};

function normalizeHeader(h: string): string {
  return h.trim().toLowerCase().replace(/[^a-z0-9]/g, '_').replace(/__+/g, '_').replace(/^_+|_+$/g, '');
}

function findHeaderIndex(normalizedHeaders: string[], canonical: string): number {
  const aliases = COLUMN_ALIASES[canonical] ?? [canonical];
  for (const alias of aliases) {
    const normAlias = normalizeHeader(alias);
    const idx = normalizedHeaders.findIndex((h) => h === normAlias || h.includes(normAlias) || normAlias.includes(h));
    if (idx >= 0) return idx;
  }
  return -1;
}

function splitCSVLine(line: string): string[] {
  const out: string[] = [];
  let cur = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === ',' && !inQuotes) {
      out.push(cur.trim());
      cur = '';
    } else {
      cur += ch;
    }
  }
  out.push(cur.trim());
  return out.map((v) => v.replace(/^"(.*)"$/s, '$1').trim());
}

function parseDateValue(raw: string): string {
  if (!raw) return '';
  const s = raw.trim();
  // already ISO?
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
    return isNaN(Date.parse(s)) ? '' : s;
  }
  // Excel serial? (number between 20000 and 60000)
  if (/^\d{4,5}(\.\d+)?$/.test(s)) {
    const n = Number(s);
    if (n > 20000 && n < 60000) {
      const base = new Date(Date.UTC(1899, 11, 30));
      const d = new Date(base.getTime() + n * 86400000);
      return d.toISOString().split('T')[0] ?? '';
    }
  }
  // DD/MM/YYYY or DD-MM-YYYY or MM/DD/YYYY
  const dmy = s.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$/);
  if (dmy) {
    const a = parseInt(dmy[1] ?? '0', 10);
    const b = parseInt(dmy[2] ?? '0', 10);
    const y = parseInt(dmy[3] ?? '0', 10);
    // Heuristic: if a >12 assume DD/MM, else try MM/DD then DD/MM
    let d: Date | null = null;
    if (a > 12) {
      d = new Date(y, b - 1, a);
    } else if (b > 12) {
      d = new Date(y, a - 1, b);
    } else {
      // ambiguous, prefer DD/MM if a <=12 and b <=12 -> treat as DD/MM? fallback to Date.parse
      const parsed = Date.parse(s);
      if (!isNaN(parsed)) return new Date(parsed).toISOString().split('T')[0] ?? '';
      d = new Date(y, b - 1, a);
    }
    if (d && !isNaN(d.getTime())) return d.toISOString().split('T')[0] ?? '';
  }
  const parsed = Date.parse(s);
  if (!isNaN(parsed)) return new Date(parsed).toISOString().split('T')[0] ?? '';
  return '';
}

const ISIN_RE = /^[A-Z]{2}[A-Z0-9]{9}[0-9]$/;
function isValidISIN(v: string): boolean {
  if (!v) return true; // optional
  return ISIN_RE.test(v.trim().toUpperCase().replace(/[^A-Z0-9]/g, ''));
}

function isValidCurrency(code: string): boolean {
  return /^[A-Z]{3}$/.test(code);
}

interface ParseResult {
  rows: ParsedRow[];
  rowErrors: RowError[];
  globalErrors: string[];
  headers: string[];
  normalizedHeaders: string[];
  columnMap: Record<string, number | null>;
}

function parseCSV(text: string): ParseResult {
  const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
  if (lines.length < 1) return { rows: [], rowErrors: [], globalErrors: ['File is empty'], headers: [], normalizedHeaders: [], columnMap: {} };
  const rawHeaders = splitCSVLine(lines[0] ?? '');
  const normalizedHeaders = rawHeaders.map(normalizeHeader);
  const columnMap: Record<string, number | null> = {};
  for (const k of Object.keys(COLUMN_ALIASES)) {
    const idx = findHeaderIndex(normalizedHeaders, k);
    columnMap[k] = idx >= 0 ? idx : null;
  }
  const required: Array<keyof typeof COLUMN_ALIASES> = ['name', 'currency', 'principal_outstanding'];
  // Check missing required columns (at least name/currency/principal)
  const missing = required.filter((f) => columnMap[f] === null);
  if (missing.length > 0) {
    return {
      rows: [],
      rowErrors: [],
      globalErrors: [`Missing required columns: ${missing.join(', ')} (detected: ${rawHeaders.join(', ')})`],
      headers: rawHeaders,
      normalizedHeaders,
      columnMap,
    };
  }
  const rows: ParsedRow[] = [];
  const rowErrors: RowError[] = [];
  const globalErrors: string[] = [];

  for (let i = 1; i < lines.length; i++) {
    const vals = splitCSVLine(lines[i] ?? '');
    // pad vals
    while (vals.length < rawHeaders.length) vals.push('');
    const get = (canonical: string): string => {
      const idx = columnMap[canonical];
      if (idx === null || idx === undefined || idx < 0) return '';
      return (vals[idx] ?? '').trim();
    };
    const lineNo = i + 1;
    const name = get('name');
    const currencyRaw = get('currency');
    const currency = currencyRaw.toUpperCase().replace(/[^A-Z]/g, '');
    const principalStr = get('principal_outstanding');
    const principalClean = principalStr.replace(/[^0-9.\-]/g, '');
    const principal = parseFloat(principalClean);
    const couponStr = get('coupon') || '0';
    // handle percent: if coupon >1 maybe it's percent (e.g. 4.25 means 4.25%)
    let couponRaw = parseFloat(couponStr.replace(/[^0-9.\-]/g, ''));
    if (isNaN(couponRaw)) couponRaw = 0;
    // If coupon looks like percent >1, convert to decimal (4.25 -> 0.0425) if >1
    // But spec stores coupon_rate as decimal; we accept both. Keep heuristic: if couponRaw >1 then treat as percent
    let coupon = couponRaw;
    if (couponRaw > 1) coupon = couponRaw / 100;
    // also handle coupon string like "4.25%"
    if (couponStr.includes('%') && couponRaw <= 1) {
      // already handled? if user wrote 0.0425% unrealistic -> keep as is
    }
    const maturityRaw = get('maturity_date');
    const maturity = parseDateValue(maturityRaw);
    const spreadStr = get('spread') || '0';
    const spread = parseFloat(spreadStr.replace(/[^0-9.\-]/g, '')) || 0;
    const callableRaw = get('callable');
    const callable = ['true', 'yes', '1', 'y', 'callable'].includes(callableRaw.toLowerCase());
    const isinRaw = get('isin');
    const isin = isinRaw ? isinRaw.toUpperCase().replace(/[^A-Z0-9]/g, '') : undefined;
    const issueRaw = get('issue_date');
    const issue_date = issueRaw ? parseDateValue(issueRaw) : '';

    const errors: string[] = [];
    if (!name) errors.push('Missing instrument name');
    if (!currency || !isValidCurrency(currency)) errors.push(`Invalid currency "${currencyRaw}" (expect 3-letter code)`);
    if (principalStr === '' || isNaN(principal) || principal <= 0) errors.push(`Invalid principal "${principalStr}"`);
    if (!isNaN(coupon) && (coupon < 0 || coupon > 1)) {
      // after conversion coupon should be 0..1; if still >1 it's invalid
      if (coupon > 1) errors.push(`Coupon out of range "${couponStr}"`);
    }
    if (maturityRaw && !maturity) errors.push(`Invalid maturity_date "${maturityRaw}"`);
    if (spreadStr && isNaN(spread)) errors.push(`Invalid spread "${spreadStr}"`);
    if (isin && !isValidISIN(isin)) errors.push(`Invalid ISIN "${isinRaw}" (expect 12-char, e.g. US0378331005)`);
    if (maturity && issue_date && maturity < issue_date) errors.push('Maturity before issue date');

    if (errors.length > 0) {
      for (const msg of errors) rowErrors.push({ rowIndex: lineNo, field: undefined, message: `Row ${lineNo}: ${msg}` });
      // still push row if at least name/currency/principal semi-valid? For preview, push with errors flagged
      rows.push({
        name: name || `(row ${lineNo})`,
        type: get('instrument_type') || 'bond',
        currency: currency || currencyRaw.toUpperCase() || 'USD',
        principal: isNaN(principal) || principal <= 0 ? 0 : principal,
        coupon: isNaN(coupon) ? 0 : coupon,
        maturity: maturity || maturityRaw,
        spread,
        callable,
        isin,
        issue_date: issue_date || undefined,
      });
    } else {
      rows.push({
        name,
        type: get('instrument_type') || 'bond',
        currency,
        principal,
        coupon,
        maturity,
        spread,
        callable,
        isin,
        issue_date: issue_date || undefined,
      });
    }
  }

  // global duplicate check
  const seen = new Set<string>();
  for (const r of rows) {
    const key = r.name.toLowerCase();
    if (seen.has(key)) globalErrors.push(`Duplicate instrument name "${r.name}"`);
    else seen.add(key);
  }

  return { rows, rowErrors, globalErrors, headers: rawHeaders, normalizedHeaders, columnMap };
}

function validateData(rows: ParsedRow[], rowErrors: RowError[]): ValidationCheck[] {
  const checks: ValidationCheck[] = [];
  checks.push({ label: `${rows.length} instruments detected`, passed: rows.length > 0, detail: rows.length === 0 ? 'No rows after parsing' : undefined });
  const validCurrencies = rows.every((r) => isValidCurrency(r.currency));
  checks.push({ label: 'Currency data valid', passed: validCurrencies && rows.length > 0, detail: validCurrencies ? undefined : 'Some currency codes are invalid (see row errors)' });
  const validPrincipals = rows.every((r) => r.principal > 0);
  checks.push({ label: 'Principal amounts valid', passed: validPrincipals, detail: validPrincipals ? undefined : 'Some principals are zero or negative' });
  const validDates = rows.filter((r) => r.maturity).every((r) => !isNaN(Date.parse(r.maturity)));
  checks.push({ label: 'Maturity dates valid', passed: validDates, detail: validDates ? undefined : 'Some maturity dates could not be parsed' });
  const hasRowErrors = rowErrors.length === 0;
  checks.push({ label: 'Row-level validation', passed: hasRowErrors, detail: hasRowErrors ? undefined : `${rowErrors.length} row error(s) found` });
  const uniqueNames = new Set(rows.map((r) => r.name.toLowerCase()));
  const noDuplicates = uniqueNames.size === rows.length;
  checks.push({ label: 'No duplicate records', passed: noDuplicates, detail: noDuplicates ? undefined : `Found ${rows.length - uniqueNames.size} duplicate name(s)` });
  const isinValid = rows.every((r) => !r.isin || isValidISIN(r.isin));
  checks.push({ label: 'ISIN format (if present)', passed: isinValid, detail: isinValid ? undefined : 'Some ISINs have invalid format' });
  const allPassed = checks.every((c) => c.passed);
  checks.push({ label: 'Portfolio ready', passed: allPassed && rows.length > 0 });
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
  const [rowErrors, setRowErrors] = useState<RowError[]>([]);
  const [globalErrors, setGlobalErrors] = useState<string[]>([]);
  const [validationChecks, setValidationChecks] = useState<ValidationCheck[]>([]);
  const [fileName, setFileName] = useState('');
  const [previewRows, setPreviewRows] = useState<string[][]>([]);
  const [headers, setHeaders] = useState<string[]>([]);
  const [columnMap, setColumnMap] = useState<Record<string, number | null>>({});

  const handleParseResult = useCallback((result: ParseResult, preview: string[][]) => {
    setHeaders(result.headers);
    setColumnMap(result.columnMap);
    setParsedRows(result.rows);
    setRowErrors(result.rowErrors);
    setGlobalErrors(result.globalErrors);
    setValidationChecks(validateData(result.rows, result.rowErrors));
    setPreviewRows(preview);
    if (result.globalErrors.length > 0 && result.rows.length === 0) {
      // stay on method? go to validate to show errors
      setStep('validate');
    } else if (result.rows.length > 0) {
      setStep('validate');
    } else {
      setError(result.globalErrors.join('; ') || 'No valid rows found');
    }
  }, []);

  const handleFile = useCallback(async (file: File) => {
    setError('');
    setFileName(file.name);
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext !== 'csv' && ext !== 'xlsx' && ext !== 'xls') {
      setError('Unsupported file format. Please upload CSV, XLSX, or XLS.');
      return;
    }
    try {
      if (ext === 'csv') {
        const text = await file.text();
        if (!text.trim()) { setError('File is empty.'); return; }
        const previewLines = text.split(/\r?\n/).filter((l) => l.trim()).slice(0, 6);
        const preview = previewLines.map((l) => splitCSVLine(l));
        const result = parseCSV(text);
        handleParseResult(result, preview);
      } else {
        // XLSX/XLS: try SheetJS
        const buffer = await file.arrayBuffer();
        let textForPreview = '';
        let parseResult: ParseResult | null = null;
        try {
          // @ts-ignore - xlsx may not be installed; dynamic import with vite-ignore
          const xlsx: unknown = await import(/* @vite-ignore */ 'xlsx').catch(() => null);
          if (!xlsx) throw new Error('no_xlsx');
          const mod = xlsx as { read: (data: ArrayBuffer, opts: unknown) => { SheetNames: string[]; Sheets: Record<string, unknown> }; utils: { sheet_to_csv: (s: unknown) => string; sheet_to_json: (s: unknown, opts: unknown) => unknown[][] } };
          const wb = mod.read(buffer, { type: 'array' });
          const firstSheet = wb.SheetNames[0];
          if (!firstSheet) throw new Error('Workbook has no sheets');
          const sheet = wb.Sheets[firstSheet];
          const csv = mod.utils.sheet_to_csv(sheet as never);
          // Also build preview via sheet_to_json with header:1
          const json = mod.utils.sheet_to_json(sheet as never, { header: 1 }) as unknown[][];
          const preview = (json as string[][]).slice(0, 6).map((row) => (row as unknown[]).map((v) => String(v ?? '')));
          textForPreview = csv;
          parseResult = parseCSV(csv);
          handleParseResult(parseResult, preview);
        } catch (e) {
          const msg = e instanceof Error ? e.message : String(e);
          if (msg === 'no_xlsx') {
            setError('XLSX support requires SheetJS (xlsx). Please install "xlsx" (npm install xlsx) or convert your file to CSV and re-upload. Attempting to read as CSV fallback...');
            // fallback try as text
            try {
              const decoder = new TextDecoder('utf-8');
              const fallbackText = decoder.decode(buffer);
              if (fallbackText.includes(',') && fallbackText.split('\n').length > 1) {
                const previewLines = fallbackText.split(/\r?\n/).filter((l) => l.trim()).slice(0, 6);
                const preview = previewLines.map((l) => splitCSVLine(l));
                const result = parseCSV(fallbackText);
                handleParseResult(result, preview);
                return;
              }
            } catch { /* ignore */ }
            setError('XLSX parsing unavailable. Please convert to CSV (e.g., Save As → CSV in Excel) and re-upload. If you need XLSX, run: npm install xlsx');
            return;
          }
          // try fallback: if file is actually CSV with xlsx extension
          textForPreview = new TextDecoder().decode(buffer.slice(0, 4096));
          setError(`Failed to parse Excel file: ${msg}. If this is a CSV file, rename to .csv and retry.`);
          if (textForPreview.includes(',')) {
            const result = parseCSV(textForPreview);
            if (result.rows.length > 0) handleParseResult(result, [[...result.headers], ...result.rows.slice(0, 5).map((r) => [r.name, r.type, r.currency, String(r.principal), String(r.coupon), r.maturity])]);
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to read file.');
    }
  }, [handleParseResult]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) void handleFile(file);
  }, [handleFile]);

  const handleMethodSelect = (m: ImportMethod) => {
    setMethod(m);
    if (m === 'demo') {
      const demo = MOCK_PORTFOLIOS[0];
      if (!demo) return;
      setName(demo.name);
      setDescription(demo.description);
      const rows: ParsedRow[] = demo.instruments.map((i) => ({
        name: i.name, type: i.instrument_type, currency: i.currency,
        principal: i.principal_outstanding, coupon: i.coupon_rate,
        maturity: i.maturity_date, spread: i.spread_bps, callable: i.is_callable,
      }));
      setParsedRows(rows);
      setRowErrors([]);
      setGlobalErrors([]);
      setValidationChecks(validateData(rows, []));
      setPreviewRows([['name','type','currency','principal','coupon','maturity','spread','callable'], ...rows.slice(0,5).map((r)=>[r.name,r.type,r.currency,String(r.principal),String(r.coupon),r.maturity])]);
      setHeaders(['name','type','currency','principal','coupon','maturity','spread','callable']);
      setColumnMap({ name:0, instrument_type:1, currency:2, principal_outstanding:3, coupon:4, maturity_date:5, spread:6, callable:7 });
      setStep('validate');
    } else if (m === 'manual') {
      setParsedRows([]);
      setRowErrors([]);
      setGlobalErrors([]);
      setValidationChecks([]);
      setStep('configure');
    }
  };

  const handleProceedFromValidation = () => {
    const failed = validationChecks.filter((c) => !c.passed && c.label !== 'Portfolio ready');
    if (failed.length > 0) return;
    setStep('configure');
  };

  const handleAddInstrument = () => {
    setParsedRows((prev) => [
      ...prev,
      { name: `Instrument ${prev.length + 1}`, type: 'bond', currency: 'USD', principal: 1000000, coupon: 0.03, maturity: new Date(Date.now() + 365*86400000*5).toISOString().split('T')[0] ?? '', spread: 0, callable: false },
    ]);
  };

  const handleRemoveInstrument = (idx: number) => {
    setParsedRows((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleUpdateInstrument = (idx: number, patch: Partial<ParsedRow>) => {
    setParsedRows((prev) => prev.map((r, i) => i === idx ? { ...r, ...patch } : r));
  };

  const handleSubmit = async () => {
    if (!name.trim()) { setError('Portfolio name is required.'); return; }
    if (parsedRows.length === 0 && method !== 'upload') {
      setError('Add at least one instrument or import a file.');
      return;
    }
    // final row validation before submit
    const finalErrors: RowError[] = [];
    parsedRows.forEach((r, i) => {
      if (!r.name.trim()) finalErrors.push({ rowIndex: i+1, message: `Row ${i+1}: Missing name` });
      if (!isValidCurrency(r.currency)) finalErrors.push({ rowIndex: i+1, message: `Row ${i+1}: Invalid currency` });
      if (r.principal <= 0) finalErrors.push({ rowIndex: i+1, message: `Row ${i+1}: Invalid principal` });
      if (r.maturity && isNaN(Date.parse(r.maturity))) finalErrors.push({ rowIndex: i+1, message: `Row ${i+1}: Invalid maturity date` });
      if (r.isin && !isValidISIN(r.isin)) finalErrors.push({ rowIndex: i+1, message: `Row ${i+1}: Invalid ISIN` });
    });
    if (finalErrors.length > 0) {
      setRowErrors(finalErrors);
      setError(`Please fix ${finalErrors.length} instrument error(s) before creating portfolio.`);
      return;
    }
    setError('');
    setLoading(true);
    try {
      if (method === 'upload' && fileName) {
        // Try bulk upload via FormData first, fallback to JSON creation
        try {
          const headerLine = headers.join(',') || 'name,instrument_type,currency,principal_outstanding,coupon,maturity_date,spread_bps,is_callable,isin';
          const dataLines = parsedRows.map((r) =>
            [r.name, r.type, r.currency, String(r.principal), String(r.coupon), r.maturity, String(r.spread), String(r.callable), r.isin ?? ''].join(',')
          );
          const blob = new Blob([headerLine + '\n' + dataLines.join('\n')], { type: 'text/csv' });
          const file = new File([blob], `${name.replace(/\s+/g, '_')}.csv`, { type: 'text/csv' });
          const formData = new FormData();
          formData.append('file', file);
          formData.append('name', name);
          formData.append('description', description);
          // prefer bulkImport if available, else upload
          const portfolio = await (api.portfolios as unknown as { bulkImport: (fd: FormData) => Promise<{ id:string}> }).bulkImport
            ? await (api.portfolios as unknown as { bulkImport: (fd: FormData)=>Promise<{id:string}>}).bulkImport(formData)
            : await api.portfolios.upload(formData);
          navigate(`/portfolios/${(portfolio as { id:string}).id}`);
          return;
        } catch {
          // fallback to JSON create
        }
      }
      const instruments = parsedRows.map((r) => ({
        name: r.name, instrument_type: r.type, currency: r.currency,
        principal_outstanding: r.principal, coupon_rate: r.coupon,
        maturity_date: r.maturity, spread_bps: r.spread,
        is_callable: r.callable, issue_date: r.issue_date || new Date().toISOString().split('T')[0],
        ...(r.isin ? { isin: r.isin } : {}),
      }));
      const portfolio = await api.portfolios.create({ name, description, instruments });
      navigate(`/portfolios/${portfolio.id}`);
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

  const validationFailed = validationChecks.some((c) => !c.passed && c.label !== 'Portfolio ready');

  return (
    <AppShell>
      <div className="px-8 py-6 max-w-5xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">New Portfolio</h1>
          <p className="mt-1 text-sm text-slate-500">Import or create a new debt portfolio for analysis</p>
        </div>
        <StepIndicator current={step} />

        {error && (
          <div className="mb-6 glass-card border-red-200/40 bg-red-500/10 backdrop-blur-xl p-4 text-sm text-red-700 rounded-xl">{error}</div>
        )}

        {step === 'method' && (
          <div className="space-y-4">
            <div
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              className={`glass-card p-8 text-center cursor-pointer transition-all border-2 border-dashed ${dragOver ? 'border-blue-400 bg-blue-50/40 scale-[1.01] shadow-lg' : 'border-white/60 hover:border-blue-300 hover:bg-white/60 hover:shadow-md'}`}
            >
              <div className="flex flex-col items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-blue-500/10 backdrop-blur-md border border-blue-500/10 flex items-center justify-center">
                  <svg className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-900">Upload CSV / Excel file</p>
                  <p className="text-xs text-slate-500 mt-1">Drag and drop or click to browse. Supports CSV, XLSX, XLS. Auto-maps columns: instrument_type, currency, principal_outstanding, maturity_date, coupon…</p>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  {['.csv', '.xlsx', '.xls'].map((ext) => (
                    <span key={ext} className="px-2 py-0.5 text-xs font-medium bg-white/70 backdrop-blur-md border border-white/50 text-slate-600 rounded-full">{ext}</span>
                  ))}
                </div>
                {fileName && <Badge variant="info" size="sm">Selected: {fileName}</Badge>}
              </div>
              <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls" className="hidden"
                onChange={(e) => { const file = e.target.files?.[0]; if (file) void handleFile(file); }} />
            </div>

            <button onClick={() => handleMethodSelect('demo')} className="w-full glass-card p-5 text-left hover:bg-white/70 hover:border-slate-200/60 transition-all group border border-white/40">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/10 backdrop-blur-md border border-emerald-500/10 flex items-center justify-center group-hover:bg-emerald-100 transition-colors">
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

            <button onClick={() => handleMethodSelect('manual')} className="w-full glass-card p-5 text-left hover:bg-white/70 hover:border-slate-200/60 transition-all group border border-white/40">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-violet-500/10 backdrop-blur-md border border-violet-500/10 flex items-center justify-center group-hover:bg-violet-100 transition-colors">
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
                subtitle={fileName ? `File: ${fileName} • ${headers.length} columns detected` : 'Demonstration dataset'}
                action={method === 'upload' ? (
                  <Button variant="ghost" size="sm" onClick={() => { setStep('method'); setFileName(''); setParsedRows([]); setRowErrors([]); setGlobalErrors([]); }}>Change file</Button>
                ) : undefined}
              />
              {headers.length > 0 && (
                <div className="mb-6 p-3 glass-card bg-white/40 border border-white/30 rounded-xl">
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">Column mapping</p>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(COLUMN_ALIASES).map(([canonical]) => {
                      const idx = columnMap[canonical];
                      const detected = idx !== null && idx !== undefined && idx >= 0 ? headers[idx] : null;
                      return (
                        <span key={canonical} className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold tracking-wide border backdrop-blur-md shadow-sm ${detected ? 'bg-emerald-500/10 text-emerald-700 border-emerald-500/20' : 'bg-slate-100/70 text-slate-500 border-slate-200/50'}`}>
                          {canonical} {detected ? `→ ${detected}` : '• not found'}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}
              {previewRows.length > 0 && (
                <div className="mb-6">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Preview (first {previewRows.length - 1} rows) — before confirm</p>
                  <div className="overflow-x-auto glass-card p-0 border border-white/40 rounded-xl">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="bg-white/60 backdrop-blur-md">
                          {previewRows[0]?.map((h, i) => (
                            <th key={i} className="px-3 py-2 text-left font-semibold text-slate-600 whitespace-nowrap">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/30">
                        {previewRows.slice(1).map((row, ri) => {
                          const errs = rowErrors.filter((e) => e.rowIndex === ri + 2);
                          const hasErr = errs.length > 0;
                          return (
                            <tr key={ri} className={`${hasErr ? 'bg-red-50/60' : 'hover:bg-white/60'} transition-colors`}>
                              {row.map((cell, ci) => (
                                <td key={ci} className="px-3 py-2 text-slate-700 whitespace-nowrap max-w-[160px] truncate">{cell}</td>
                              ))}
                              {hasErr && (
                                <td className="px-3 py-2">
                                  <div className="flex flex-wrap gap-1">
                                    {errs.map((e, k) => <Badge key={k} variant="danger" size="sm">{e.message.replace(/^Row \d+:\s*/, '')}</Badge>)}
                                  </div>
                                </td>
                              )}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
              <div className="space-y-2.5">
                {validationChecks.map((check, i) => (
                  <div key={i} className="flex items-center gap-3">
                    {check.passed ? (
                      <div className="w-5 h-5 rounded-full bg-emerald-500/15 border border-emerald-500/20 backdrop-blur-md flex items-center justify-center flex-shrink-0">
                        <svg className="h-3 w-3 text-emerald-600" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                        </svg>
                      </div>
                    ) : (
                      <div className="w-5 h-5 rounded-full bg-red-500/15 border border-red-500/20 backdrop-blur-md flex items-center justify-center flex-shrink-0">
                        <svg className="h-3 w-3 text-red-600" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </div>
                    )}
                    <Badge variant={check.passed ? 'success' : 'danger'} size="sm">{check.passed ? '✓' : '✗'}</Badge>
                    <span className={`text-sm ${check.passed ? 'text-slate-700' : 'text-red-600'}`}>
                      {check.label}
                    </span>
                    {check.detail && <span className="text-xs text-slate-400 ml-1">— {check.detail}</span>}
                  </div>
                ))}
              </div>
              {(rowErrors.length > 0 || globalErrors.length > 0) && (
                <div className="mt-4 p-3 glass-card bg-red-500/10 border border-red-200/40 backdrop-blur-xl rounded-xl">
                  <p className="text-xs font-semibold text-red-700 mb-1">Errors — per row</p>
                  <ul className="space-y-1">
                    {[...globalErrors, ...rowErrors.map((e)=>e.message)].slice(0, 12).map((err, i) => (
                      <li key={i} className="text-xs text-red-600 flex items-start gap-1.5"><Badge variant="danger" size="sm">!</Badge> {err}</li>
                    ))}
                    {(globalErrors.length + rowErrors.length) > 12 && (
                      <li className="text-xs text-red-500">...and {globalErrors.length + rowErrors.length - 12} more</li>
                    )}
                  </ul>
                </div>
              )}
            </Card>
            <div className="flex items-center justify-between">
              <Button variant="ghost" onClick={() => { setStep('method'); setFileName(''); setParsedRows([]); }}>Back</Button>
              <Button variant="primary" onClick={handleProceedFromValidation} disabled={validationFailed}>
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
                    className="w-full px-3.5 py-2.5 glass-input rounded-xl text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none transition-all" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Description</label>
                  <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3}
                    placeholder="Brief description of the portfolio purpose and scope..."
                    className="w-full px-3.5 py-2.5 glass-input rounded-xl text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none transition-all resize-none" />
                </div>
              </div>
            </Card>

            <Card>
              <CardHeader title={parsedRows.length > 0 ? 'Detected Instruments' : 'Instruments (manual entry)'} subtitle={parsedRows.length > 0 ? `${parsedRows.length} instruments ready for import — add/remove still available` : 'No instruments yet — add manually or go back to import'}
                action={
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1.5">{Array.from(new Set(parsedRows.map((r) => r.currency))).map((c) => (
                      <Badge key={c} variant="info" size="sm">{c}</Badge>
                    ))}</div>
                    <Button variant="secondary" size="sm" onClick={handleAddInstrument}>+ Add instrument</Button>
                  </div>
                } />
              {parsedRows.length > 0 ? (
                <div className="overflow-x-auto glass-card p-0 border border-white/40 rounded-xl max-h-[420px] overflow-y-auto">
                  <table className="w-full text-xs">
                    <thead className="sticky top-0 bg-white/80 backdrop-blur-md z-10">
                      <tr className="border-b border-white/40">
                        {['Name', 'Type', 'CCY', 'Principal', 'Coupon', 'Maturity', 'Spread', 'Callable', 'ISIN', ''].map((h) => (
                          <th key={h} className={`px-3 py-2 font-semibold text-slate-500 ${['Principal', 'Coupon', 'Spread'].includes(h) ? 'text-right' : h === 'Callable' ? 'text-center' : 'text-left'}`}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100/50">
                      {parsedRows.map((row, i) => {
                        const errs = rowErrors.filter((e) => e.rowIndex === i+1);
                        const isValid = !errs.length && row.principal>0 && isValidCurrency(row.currency) && (!row.maturity || !isNaN(Date.parse(row.maturity))) && (!row.isin || isValidISIN(row.isin));
                        return (
                          <tr key={i} className={`${!isValid ? 'bg-red-50/40' : 'hover:bg-white/60'} transition-colors`}>
                            <td className="px-2 py-1.5">
                              <input value={row.name} onChange={(e)=>handleUpdateInstrument(i,{name:e.target.value})} className="glass-input py-1.5 px-2 text-xs w-[160px]" placeholder="Name" />
                            </td>
                            <td className="px-2 py-1.5">
                              <input value={row.type} onChange={(e)=>handleUpdateInstrument(i,{type:e.target.value})} className="glass-input py-1.5 px-2 text-xs w-[110px]" placeholder="type" />
                            </td>
                            <td className="px-2 py-1.5">
                              <input value={row.currency} onChange={(e)=>handleUpdateInstrument(i,{currency:e.target.value.toUpperCase()})} className="glass-input py-1.5 px-2 text-xs w-[70px] text-center" placeholder="USD" maxLength={3} />
                            </td>
                            <td className="px-2 py-1.5">
                              <input type="number" value={row.principal} onChange={(e)=>handleUpdateInstrument(i,{principal: parseFloat(e.target.value)||0})} className="glass-input py-1.5 px-2 text-xs w-[120px] text-right" />
                            </td>
                            <td className="px-2 py-1.5">
                              <input type="number" step="0.0001" value={row.coupon} onChange={(e)=>handleUpdateInstrument(i,{coupon: parseFloat(e.target.value)||0})} className="glass-input py-1.5 px-2 text-xs w-[80px] text-right" />
                            </td>
                            <td className="px-2 py-1.5">
                              <input type="date" value={row.maturity} onChange={(e)=>handleUpdateInstrument(i,{maturity:e.target.value})} className="glass-input py-1.5 px-2 text-xs w-[135px]" />
                            </td>
                            <td className="px-2 py-1.5">
                              <input type="number" value={row.spread} onChange={(e)=>handleUpdateInstrument(i,{spread: parseFloat(e.target.value)||0})} className="glass-input py-1.5 px-2 text-xs w-[70px] text-right" />
                            </td>
                            <td className="px-2 py-1.5 text-center">
                              <input type="checkbox" checked={row.callable} onChange={(e)=>handleUpdateInstrument(i,{callable:e.target.checked})} className="rounded border-slate-300" />
                            </td>
                            <td className="px-2 py-1.5">
                              <input value={row.isin ?? ''} onChange={(e)=>handleUpdateInstrument(i,{isin:e.target.value.toUpperCase()})} className="glass-input py-1.5 px-2 text-xs w-[120px]" placeholder="ISIN" maxLength={12} />
                            </td>
                            <td className="px-2 py-1.5">
                              <div className="flex items-center gap-1">
                                {!isValid && <Badge variant="danger" size="sm">!</Badge>}
                                {isValid && <Badge variant="success" size="sm">✓</Badge>}
                                <button onClick={()=>handleRemoveInstrument(i)} className="p-1 rounded-md hover:bg-red-50 text-slate-400 hover:text-red-600 transition-colors" title="Remove">
                                  <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="glass-card p-8 text-center border border-dashed border-white/60">
                  <p className="text-sm text-slate-500">No instruments yet. Use <Badge variant="info" size="sm">+ Add instrument</Badge> to create one manually, or go back to import a file.</p>
                  <div className="mt-4 flex justify-center gap-2">
                    <Button variant="primary" size="sm" onClick={handleAddInstrument}>Add first instrument</Button>
                    <Button variant="ghost" size="sm" onClick={()=>setStep('method')}>Back to import</Button>
                  </div>
                </div>
              )}
              {rowErrors.length > 0 && (
                <div className="mt-4 p-3 glass-card bg-amber-500/10 border border-amber-200/40 rounded-xl">
                  <p className="text-xs font-semibold text-amber-800 mb-1 flex items-center gap-1.5"><Badge variant="warning" size="sm">{rowErrors.length}</Badge> Validation warnings — fix before create</p>
                  <ul className="space-y-1">
                    {rowErrors.slice(0,6).map((e,i)=><li key={i} className="text-xs text-amber-700">{e.message}</li>)}
                    {rowErrors.length>6 && <li className="text-xs text-amber-600">...and {rowErrors.length-6} more</li>}
                  </ul>
                </div>
              )}
            </Card>

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
