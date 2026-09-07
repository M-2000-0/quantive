import { useState } from 'react';
import {
  FileText, ArrowRight, CheckCircle, AlertTriangle,
  Download, Upload, RefreshCw
} from 'lucide-react';
import { api } from '../api';

type FormatType = 'fpml' | 'xbrl' | 'swift_mt3' | 'csv' | 'json';

const FORMAT_OPTIONS: { value: FormatType; label: string; description: string }[] = [
  { value: 'fpml', label: 'FpML', description: 'Financial Products Markup Language' },
  { value: 'xbrl', label: 'XBRL', description: 'eXtensible Business Reporting Language' },
  { value: 'swift_mt3', label: 'SWIFT MT3', description: 'SWIFT message format for treasury' },
  { value: 'csv', label: 'CSV', description: 'Comma-separated values' },
  { value: 'json', label: 'JSON', description: 'JavaScript Object Notation' },
];

export default function InteroperabilityPage() {
  const [sourceFormat, setSourceFormat] = useState<FormatType>('fpml');
  const [targetFormat, setTargetFormat] = useState<FormatType>('json');
  const [inputContent, setInputContent] = useState('');
  const [outputContent, setOutputContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [validationResult, setValidationResult] = useState<any>(null);

  const handleConvert = async () => {
    if (!inputContent.trim()) return;
    setLoading(true);
    setError('');
    setOutputContent('');
    try {
      const result = await api.interoperability.convert({
        content: inputContent,
        source_format: sourceFormat,
        target_format: targetFormat,
      });
      setOutputContent(result.converted_content || result.content || JSON.stringify(result, null, 2));
    } catch (e: any) {
      setError(e.message || 'Conversion failed');
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async () => {
    if (!inputContent.trim()) return;
    setLoading(true);
    setError('');
    try {
      const result = await api.interoperability.validate({
        content: inputContent,
        format: sourceFormat,
      });
      setValidationResult(result);
    } catch (e: any) {
      setError(e.message || 'Validation failed');
    } finally {
      setLoading(false);
    }
  };

  const handleParse = async () => {
    if (!inputContent.trim()) return;
    setLoading(true);
    setError('');
    try {
      let result;
      if (sourceFormat === 'fpml') {
        result = await api.interoperability.parseFpML(inputContent);
      } else if (sourceFormat === 'xbrl') {
        result = await api.interoperability.parseXBRL(inputContent);
      }
      setOutputContent(JSON.stringify(result, null, 2));
    } catch (e: any) {
      setError(e.message || 'Parse failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
            <FileText className="w-8 h-8 text-blue-600" />
            FpML/XBRL Interoperability
          </h1>
          <p className="text-slate-600 mt-2">
            Convert and validate financial data formats for government procurement systems.
          </p>
        </div>

        {/* Format Selection */}
        <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200 mb-6">
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-slate-700 mb-2">Source Format</label>
              <select
                value={sourceFormat}
                onChange={(e) => setSourceFormat(e.target.value as FormatType)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2"
              >
                {FORMAT_OPTIONS.map(f => (
                  <option key={f.value} value={f.value}>{f.label} - {f.description}</option>
                ))}
              </select>
            </div>
            <div className="pt-6">
              <ArrowRight className="w-6 h-6 text-slate-400" />
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-slate-700 mb-2">Target Format</label>
              <select
                value={targetFormat}
                onChange={(e) => setTargetFormat(e.target.value as FormatType)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2"
              >
                {FORMAT_OPTIONS.map(f => (
                  <option key={f.value} value={f.value}>{f.label} - {f.description}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Input/Output */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Input */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200">
            <div className="p-4 border-b border-slate-200 flex items-center justify-between">
              <h2 className="font-semibold text-slate-900">Input</h2>
              <div className="flex gap-2">
                <button
                  onClick={handleValidate}
                  disabled={!inputContent || loading}
                  className="px-3 py-1 text-sm bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 disabled:opacity-50"
                >
                  Validate
                </button>
                <button
                  onClick={handleParse}
                  disabled={!inputContent || loading}
                  className="px-3 py-1 text-sm bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 disabled:opacity-50"
                >
                  Parse
                </button>
              </div>
            </div>
            <textarea
              value={inputContent}
              onChange={(e) => setInputContent(e.target.value)}
              placeholder={`Paste your ${sourceFormat.toUpperCase()} content here...`}
              className="w-full h-80 p-4 border-none outline-none font-mono text-sm resize-none"
            />
          </div>

          {/* Output */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200">
            <div className="p-4 border-b border-slate-200 flex items-center justify-between">
              <h2 className="font-semibold text-slate-900">Output</h2>
              {outputContent && (
                <button
                  onClick={() => {
                    const blob = new Blob([outputContent], { type: 'text/plain' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `converted.${targetFormat}`;
                    a.click();
                  }}
                  className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200"
                >
                  <Download className="w-4 h-4 inline mr-1" />
                  Download
                </button>
              )}
            </div>
            <textarea
              value={outputContent}
              readOnly
              placeholder="Converted output will appear here..."
              className="w-full h-80 p-4 border-none outline-none font-mono text-sm resize-none bg-slate-50"
            />
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
            <div className="flex items-center gap-2 text-red-700">
              <AlertTriangle className="w-5 h-5" />
              <span className="font-medium">{error}</span>
            </div>
          </div>
        )}

        {/* Validation Result */}
        {validationResult && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 mb-6">
            <div className="p-4 border-b border-slate-200">
              <h2 className="font-semibold text-slate-900">Validation Result</h2>
            </div>
            <div className="p-6">
              <div className="flex items-center gap-3 mb-4">
                {validationResult.valid ? (
                  <CheckCircle className="w-6 h-6 text-emerald-500" />
                ) : (
                  <AlertTriangle className="w-6 h-6 text-red-500" />
                )}
                <span className={`font-medium ${validationResult.valid ? 'text-emerald-700' : 'text-red-700'}`}>
                  {validationResult.valid ? 'Document is valid' : 'Document has errors'}
                </span>
              </div>
              {validationResult.errors && validationResult.errors.length > 0 && (
                <div className="space-y-2">
                  {validationResult.errors.map((err: string, idx: number) => (
                    <div key={idx} className="text-sm text-red-600 bg-red-50 p-2 rounded">
                      {err}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-center">
          <button
            onClick={handleConvert}
            disabled={!inputContent || loading}
            className="flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
          >
            {loading ? (
              <RefreshCw className="w-5 h-5 animate-spin" />
            ) : (
              <ArrowRight className="w-5 h-5" />
            )}
            Convert to {targetFormat.toUpperCase()}
          </button>
        </div>
      </div>
    </div>
  );
}
