import { useState, useCallback, useRef } from 'react';
import { Card } from './ui';
import { Button } from './ui';
import { Badge } from './ui';
import { ProgressBar } from './ui';
import { CircleCheck as CheckCircle, TriangleAlert as AlertTriangle } from 'lucide-react';

interface ParsedRow {
 [key: string]: string;
}

interface CSVImportWizardProps {
 onComplete: (data: ParsedRow[]) => void;
 onCancel: () => void;
 columnMapping?: Record<string, string>;
 requiredColumns?: string[];
}

type WizardStep = 'upload' | 'preview' | 'mapping' | 'validate' | 'import';

export default function CSVImportWizard({
 onComplete, onCancel, columnMapping = {}, requiredColumns = ['name', 'principal_outstanding'] }: CSVImportWizardProps) {
 const [step, setStep] = useState<WizardStep>('upload');
 const [file, setFile] = useState<File | null>(null);
 const [rawData, setRawData] = useState<string>('');
 const [headers, setHeaders] = useState<string[]>([]);
 const [rows, setRows] = useState<ParsedRow[]>([]);
 const [mappings, setMappings] = useState<Record<string, string>>(columnMapping);
 const [dragOver, setDragOver] = useState(false);
 const [importProgress, setImportProgress] = useState(0);
 const fileInputRef = useRef<HTMLInputElement>(null);

 const parseCSV = useCallback((text: string) => {
 const lines = text.trim().split('\n');
 if (lines.length < 2) return;

 const h = lines[0].split(',').map((h) => h.trim().replace(/^"|"$/g, ''));
 const r = lines.slice(1).map((line) => {
 const values = line.split(',').map((v) => v.trim().replace(/^"|"$/g, ''));
 const obj: ParsedRow = {};
 h.forEach((key, i) => { obj[key] = values[i] || ''; });
 return obj;
 });

 setHeaders(h);
 setRows(r);
 setRawData(text);

 // Auto-map
 const autoMap: Record<string, string> = {};
 h.forEach((header) => {
 const lower = header.toLowerCase().replace(/[\s_-]/g, '_');
 if (lower.includes('name') || lower.includes('instrument')) autoMap[header] = 'name';
 else if (lower.includes('principal') || lower.includes('amount') || lower.includes('outstanding')) autoMap[header] = 'principal_outstanding';
 else if (lower.includes('coupon') || lower.includes('rate')) autoMap[header] = 'coupon_rate';
 else if (lower.includes('maturity') || lower.includes('due')) autoMap[header] = 'maturity_date';
 else if (lower.includes('currency') || lower.includes('ccy')) autoMap[header] = 'currency';
 else if (lower.includes('type') || lower.includes('instrument')) autoMap[header] = 'instrument_type';
 else if (lower.includes('spread') || lower.includes('bps')) autoMap[header] = 'spread_bps';
 else if (lower.includes('issue')) autoMap[header] = 'issue_date';
 else if (lower.includes('callable') || lower.includes('call')) autoMap[header] = 'is_callable';
 });
 setMappings(autoMap);
 setStep('preview');
 }, []);

 const handleDrop = useCallback((e: React.DragEvent) => {
 e.preventDefault();
 setDragOver(false);
 const f = e.dataTransfer.files[0];
 if (f && (f.name.endsWith('.csv') || f.name.endsWith('.txt'))) {
 setFile(f);
 f.text().then(parseCSV);
 }
 }, [parseCSV]);

 const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
 const f = e.target.files?.[0];
 if (f) {
 setFile(f);
 f.text().then(parseCSV);
 }
 }, [parseCSV]);

 const validateData = () => {
 const mappedFields = new Set(Object.values(mappings));
 const missing = requiredColumns.filter((rc) => !mappedFields.includes(rc));
 return { valid: missing.length === 0, missingFields: missing };
 };

 const executeImport = () => {
 setStep('import');
 setImportProgress(0);
 let progress = 0;
 const interval = setInterval(() => {
 progress += 10;
 setImportProgress(progress);
 if (progress >= 100) {
 clearInterval(interval);
 // Map rows using mappings
 const mappedRows = rows.map((row) => {
 const mapped: ParsedRow = {};
 Object.entries(mappings).forEach(([csvCol, targetField]) => {
 mapped[targetField] = row[csvCol];
 });
 return mapped;
 });
 onComplete(mappedRows);
 }
 }, 50);
 };

 const validation = validateData();

 return (
 <Card className="p-6 max-w-2xl mx-auto">
 {/* Step indicator */}
 <div className="flex items-center gap-2 mb-6">
 {(['upload', 'preview', 'mapping', 'validate', 'import'] as WizardStep[]).map((s, i) => (
 <div key={s} className="flex items-center gap-2">
 <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
 step === s ? 'bg-blue-500 text-white' : i < ['upload', 'preview', 'mapping', 'validate', 'import'].indexOf(step) ? 'bg-green-500 text-white' : 'bg-white/10 text-white/40'
 }`}>
 {i < ['upload', 'preview', 'mapping', 'validate', 'import'].indexOf(step) ? '✓' : i + 1}
 </div>
 <span className={`text-xs ${step === s ? 'text-white' : 'text-white/40'}`}>
 {s.charAt(0).toUpperCase() + s.slice(1)}
 </span>
 {i < 4 && <div className="w-8 h-px bg-white/10" />}
 </div>
 ))}
 </div>

 {/* Step content */}
 {step === 'upload' && (
 <div
 onDrop={handleDrop}
 onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
 onDragLeave={() => setDragOver(false)}
 className={`border-2 border-dashed rounded-2xl p-12 text-center transition-all cursor-pointer ${
 dragOver ? 'border-blue-400 bg-blue-500/10' : 'border-white/10 hover:border-white/20 hover:bg-white/[0.02]'
 }`}
 onClick={() => fileInputRef.current?.click()}
 >
 <input ref={fileInputRef} type="file" accept=".csv,.txt" onChange={handleFileSelect} className="hidden" />
 <div className="text-4xl mb-3">📁</div>
 <p className="text-white/80 font-medium">Drop your CSV file here</p>
 <p className="text-white/40 text-sm mt-1">or click to browse • supports .csv and .txt</p>
 </div>
 )}

 {step === 'preview' && (
 <div>
 <div className="flex items-center justify-between mb-4">
 <div>
 <h3 className="font-semibold text-white">Data Preview</h3>
 <p className="text-white/50 text-sm">{rows.length} rows • {headers.length} columns</p>
 </div>
 <Badge variant="info">{file?.name}</Badge>
 </div>
 <div className="overflow-x-auto max-h-60 rounded-xl border border-white/10">
 <table className="w-full text-xs">
 <thead>
 <tr className="bg-white/5">
 {headers.map((h) => <th key={h} className="px-3 py-2 text-left text-white/60 font-medium">{h}</th>)}
 </tr>
 </thead>
 <tbody>
 {rows.slice(0, 10).map((row, i) => (
 <tr key={i} className="border-t border-white/5">
 {headers.map((h) => <td key={h} className="px-3 py-2 text-white/70">{row[h]}</td>)}
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 <div className="flex justify-end gap-2 mt-4">
 <Button variant="ghost" onClick={onCancel}>Cancel</Button>
 <Button variant="primary" onClick={() => setStep('mapping')}>Map Columns →</Button>
 </div>
 </div>
 )}

 {step === 'mapping' && (
 <div>
 <h3 className="font-semibold text-white mb-4">Map CSV Columns to Fields</h3>
 <div className="space-y-3">
 {headers.map((h) => (
 <div key={h} className="flex items-center gap-3">
 <span className="text-sm text-white/70 w-40 truncate">{h}</span>
 <span className="text-white/30">→</span>
 <select
 value={mappings[h] || ''}
 onChange={(e) => setMappings((prev) => ({ ...prev, [h]: e.target.value }))}
 className="bg-white/5 border border-white/10 rounded-xl px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 flex-1"
 >
 <option value="">— skip —</option>
 <option value="name">Name</option>
 <option value="instrument_type">Instrument Type</option>
 <option value="currency">Currency</option>
 <option value="principal_outstanding">Principal Outstanding</option>
 <option value="coupon_rate">Coupon Rate</option>
 <option value="maturity_date">Maturity Date</option>
 <option value="issue_date">Issue Date</option>
 <option value="spread_bps">Spread (bps)</option>
 <option value="is_callable">Callable</option>
 </select>
 </div>
 ))}
 </div>
 <div className="flex justify-end gap-2 mt-4">
 <Button variant="ghost" onClick={() => setStep('preview')}>← Back</Button>
 <Button variant="primary" onClick={() => setStep('validate')}>Validate →</Button>
 </div>
 </div>
 )}

 {step === 'validate' && (
 <div>
 <h3 className="font-semibold text-white mb-4">Validation</h3>
 {validation.valid ? (
 <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-4">
 <p className="text-green-400 font-medium"> <CheckCircle className="w-4 h-4 inline" /> All required fields mapped</p>
 <p className="text-white/50 text-sm mt-1">{rows.length} rows ready to import</p>
 </div>
 ) : (
 <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
 <p className="text-red-400 font-medium"> <AlertTriangle className="w-4 h-4 inline" /> Missing required fields</p>
 <p className="text-white/50 text-sm mt-1">Missing: {validation.missingFields.join(', ')}</p>
 </div>
 )}
 <div className="flex justify-end gap-2 mt-4">
 <Button variant="ghost" onClick={() => setStep('mapping')}>← Back</Button>
 <Button variant="primary" onClick={executeImport} disabled={!validation.valid}>
 Import {rows.length} Rows
 </Button>
 </div>
 </div>
 )}

 {step === 'import' && (
 <div className="text-center py-8">
 <div className="text-4xl mb-4">{importProgress >= 100 ? '🎉' : '⏳'}</div>
 <h3 className="font-semibold text-white mb-2">
 {importProgress >= 100 ? 'Import Complete!' : 'Importing...'}
 </h3>
 <ProgressBar value={importProgress} className="max-w-xs mx-auto mt-4" />
 <p className="text-white/50 text-sm mt-2">
 {importProgress >= 100 ? `${rows.length} rows imported successfully` : `${importProgress}% complete`}
 </p>
 </div>
 )}
 </Card>
 );
}
