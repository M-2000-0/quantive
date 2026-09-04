import { events } from '../lib/analytics';

/**
 * Export data in multiple formats.
 * Uses browser-native APIs (no external dependencies).
 */

export type ExportFormat = 'csv' | 'json' | 'xlsx';

// ── CSV Export ───────────────────────────────────────────────────────────────

function escapeCSV(value: unknown): string {
  if (value === null || value === undefined) return '';
  const str = String(value);
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

export function toCSV(headers: string[], rows: unknown[][]): string {
  const lines = [headers.map(escapeCSV).join(',')];
  for (const row of rows) {
    lines.push(row.map(escapeCSV).join(','));
  }
  return lines.join('\n');
}

// ── JSON Export ──────────────────────────────────────────────────────────────

export function toJSON(data: unknown, pretty = true): string {
  return JSON.stringify(data, null, pretty ? 2 : 0);
}

// ── XLSX Export (basic XML spreadsheet) ─────────────────────────────────────

export function toXLSX(headers: string[], rows: unknown[][]): string {
  let xml = '<?xml version="1.0"?>\n';
  xml += '<?mso-application progid="Excel.Sheet"?>\n';
  xml += '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"\n';
  xml += ' xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">\n';
  xml += '<Styles>\n';
  xml += '<Style ss:ID="header"><Font ss:Bold="1" ss:Size="11"/></Style>\n';
  xml += '</Styles>\n';
  xml += '<Worksheet ss:Name="Data">\n<Table>\n';

  // Header row
  xml += '<Row>';
  for (const h of headers) {
    xml += `<Cell ss:StyleID="header"><Data ss:Type="String">${escapeXML(h)}</Data></Cell>`;
  }
  xml += '</Row>\n';

  // Data rows
  for (const row of rows) {
    xml += '<Row>';
    for (const cell of row) {
      const type = typeof cell === 'number' ? 'Number' : 'String';
      const val = escapeXML(String(cell ?? ''));
      xml += `<Cell><Data ss:Type="${type}">${val}</Data></Cell>`;
    }
    xml += '</Row>\n';
  }

  xml += '</Table>\n</Worksheet>\n</Workbook>';
  return xml;
}

function escapeXML(str: string): string {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── Download Trigger ─────────────────────────────────────────────────────────

function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ── High-Level Export Functions ──────────────────────────────────────────────

export interface ExportableData {
  name: string;
  headers: string[];
  rows: unknown[][];
}

export function exportData(data: ExportableData, format: ExportFormat) {
  const timestamp = new Date().toISOString().split('T')[0];
  const baseName = `${data.name.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_${timestamp}`;

  switch (format) {
    case 'csv': {
      const csv = toCSV(data.headers, data.rows);
      downloadFile(csv, `${baseName}.csv`, 'text/csv;charset=utf-8');
      break;
    }
    case 'json': {
      // Convert rows to objects for better JSON structure
      const objects = data.rows.map(row => {
        const obj: Record<string, unknown> = {};
        data.headers.forEach((h, i) => { obj[h] = row[i]; });
        return obj;
      });
      const json = toJSON({ name: data.name, exportedAt: new Date().toISOString(), data: objects });
      downloadFile(json, `${baseName}.json`, 'application/json');
      break;
    }
    case 'xlsx': {
      const xlsx = toXLSX(data.headers, data.rows);
      downloadFile(xlsx, `${baseName}.xls`, 'application/vnd.ms-excel');
      break;
    }
  }

  events.reportExported(format);
}

// ── Portfolio-Specific Exports ───────────────────────────────────────────────

export function exportPortfolio(portfolio: {
  name: string;
  instruments: Array<{
    name: string;
    instrument_type: string;
    currency: string;
    principal_outstanding: number;
    coupon_rate: number;
    maturity_date: string;
    spread_bps: number;
    is_callable: boolean;
  }>;
}, format: ExportFormat = 'csv') {
  exportData({
    name: portfolio.name,
    headers: ['Name', 'Type', 'Currency', 'Principal', 'Coupon Rate', 'Maturity', 'Spread (bps)', 'Callable'],
    rows: portfolio.instruments.map(i => [
      i.name,
      i.instrument_type.replace(/_/g, ' '),
      i.currency,
      i.principal_outstanding,
      `${(i.coupon_rate * 100).toFixed(2)}%`,
      i.maturity_date,
      i.spread_bps,
      i.is_callable ? 'Yes' : 'No',
    ]),
  }, format);
}

export function exportOptimizationResults(results: {
  name: string;
  strategies: Array<{
    name: string;
    rank: number;
    metrics: Record<string, unknown>;
  }>;
}, format: ExportFormat = 'csv') {
  const allMetricKeys = new Set<string>();
  results.strategies.forEach(s => Object.keys(s.metrics).forEach(k => allMetricKeys.add(k)));
  const metricCols = Array.from(allMetricKeys);

  exportData({
    name: results.name,
    headers: ['Strategy', 'Rank', ...metricCols],
    rows: results.strategies.map(s => [
      s.name,
      s.rank,
      ...metricCols.map(k => s.metrics[k] ?? ''),
    ]),
  }, format);
}

export function exportAuditLog(events: Array<{
  created_at: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  actor_email: string | null;
  metadata_json: Record<string, unknown> | null;
}>, format: ExportFormat = 'csv') {
  exportData({
    name: 'Audit Log',
    headers: ['Timestamp', 'Action', 'Resource Type', 'Resource ID', 'Actor', 'Details'],
    rows: events.map(e => [
      new Date(e.created_at).toLocaleString(),
      e.action,
      e.resource_type,
      e.resource_id ?? '',
      e.actor_email ?? 'system',
      e.metadata_json ? JSON.stringify(e.metadata_json) : '',
    ]),
  }, format);
}
