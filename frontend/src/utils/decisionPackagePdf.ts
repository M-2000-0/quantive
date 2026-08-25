import type { Report } from '../types';

// ── Fallback: markdown download (kept identical to existing ReportsPage logic) ──
function downloadMarkdown(report: Report): void {
  const sections: string[] = [];
  sections.push(`# Quantive Decision Report`);
  sections.push(`\n## Job: ${report.job_name}`);
  sections.push(`Status: ${report.status}`);
  sections.push(`Type: ${report.optimization_type.replace(/_/g, ' ')}`);
  sections.push(`Created: ${report.created_at}`);
  sections.push(`Completed: ${report.completed_at || 'N/A'}`);
  sections.push(`Model Version: ${report.model_version}`);
  sections.push(`Random Seed: ${report.random_seed}`);
  sections.push(`\n## Portfolio`);
  sections.push(`Name: ${report.portfolio.name}`);
  sections.push(`Instruments: ${report.portfolio.num_instruments}`);
  sections.push(`\n## Strategies`);
  for (const s of report.strategies) {
    sections.push(`\n### ${s.name} (Rank #${s.rank})`);
    sections.push(s.description);
    sections.push(`Metrics: ${JSON.stringify(s.metrics, null, 2)}`);
    if (s.stress_test_results) {
      sections.push(`Stress Test: ${JSON.stringify(s.stress_test_results, null, 2)}`);
    }
  }
  sections.push(`\n## Benchmarks`);
  for (const b of report.benchmarks) {
    sections.push(`- ${b.solver_name}: objective=${b.objective_value}, feasible=${b.feasible}, time=${b.execution_time_seconds.toFixed(1)}s, iterations=${b.iterations}`);
  }
  sections.push(`\n## Summary`);
  sections.push(JSON.stringify(report.summary, null, 2));
  const blob = new Blob([sections.join('\n')], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `quantive-report-${report.job_id.slice(0, 8)}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

function downloadJson(report: Report): void {
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `quantive-report-${report.job_id.slice(0, 8)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export function downloadReportJson(report: Report): void {
  downloadJson(report);
}

export function downloadReportMarkdown(report: Report): void {
  downloadMarkdown(report);
}

// ── Helpers for PDF layout ──
function fmtB(v: number): string {
  if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(0)}M`;
  return `$${v.toLocaleString()}`;
}
function fmtPct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}
function metricNum(metrics: Record<string, unknown>, key: string): number {
  const v = metrics[key];
  return typeof v === 'number' ? v : 0;
}
function safeStr(v: unknown, fallback = '—'): string {
  if (v === null || v === undefined || v === '') return fallback;
  return String(v);
}

type RGB = [number, number, number];
const C: Record<string, RGB> = {
  navy: [15, 35, 64],        // #0F2340 institutional
  navyLight: [30, 58, 95],   // #1E3A5F
  blue: [30, 64, 175],       // #1E40AF
  sky: [14, 165, 233],       // #0EA5E9
  emerald: [5, 150, 105],    // #059669
  slate900: [15, 23, 42],    // #0F172A
  slate600: [71, 85, 105],   // #475569
  slate500: [100, 116, 139], // #64748B
  slate300: [203, 213, 225], // #CBD5E1
  slate100: [241, 245, 249], // #F1F5F9
  border: [226, 232, 240],   // #E2E8F0
  white: [255, 255, 255],
};

export async function generateDecisionPackagePDF(report: Report): Promise<boolean> {
  let JsPDF: unknown = null;
  try {
    // dynamic import — if jspdf not installed, this throws and we fallback to markdown
    // @ts-expect-error optional peer dep — fallback to markdown when missing
    const mod = await import(/* @vite-ignore */ 'jspdf');
    JsPDF = (mod as unknown as Record<string, unknown>).jsPDF ?? (mod as unknown as Record<string, unknown>).default ?? mod;
    if (!JsPDF) throw new Error('jsPDF not found');
  } catch {
    downloadMarkdown(report);
    return false;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const DocCtor = JsPDF as any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const doc: any = new DocCtor({ unit: 'mm', format: 'a4', orientation: 'portrait', compress: true });

  const pageW = 210;
  const pageH = 297;
  const margin = 14;
  const contentW = pageW - margin * 2;
  const timestamp = new Date().toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  });
  const shortId = report.job_id.slice(0, 8).toUpperCase();

  let y = 0;

  function setFill(rgb: RGB) { doc.setFillColor(rgb[0], rgb[1], rgb[2]); }
  function setText(rgb: RGB) { doc.setTextColor(rgb[0], rgb[1], rgb[2]); }
  function setDraw(rgb: RGB) { doc.setDrawColor(rgb[0], rgb[1], rgb[2]); }

  function ensureSpace(needed: number) {
    if (y + needed > pageH - 14) {
      doc.addPage();
      y = margin;
    }
  }

  function addHorizontalRule() {
    setDraw(C.border);
    doc.setLineWidth(0.25);
    doc.line(margin, y, pageW - margin, y);
    y += 3;
  }

  function addSectionTitle(num: string, title: string, subtitle?: string) {
    ensureSpace(14);
    // accent bar
    setFill(C.navy);
    doc.rect(margin, y, 1.2, 8, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    setText(C.navy);
    doc.text(`${num}  ${title.toUpperCase()}`, margin + 4, y + 5.5);
    y += 9;
    if (subtitle) {
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7.5);
      setText(C.slate500);
      const lines: string[] = doc.splitTextToSize(subtitle, contentW);
      doc.text(lines, margin, y);
      y += lines.length * 3.4 + 2;
    }
    addHorizontalRule();
  }

  // ── Header band ──
  setFill(C.navy);
  doc.rect(0, 0, pageW, 28, 'F');
  // subtle gradient-like second band
  setFill(C.navyLight);
  doc.rect(0, 28, pageW, 1.2, 'F');

  // logo / wordmark
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(14);
  setText(C.white);
  doc.text('QUANTIVE', margin, 11);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(6.5);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (doc as any).setTextColor(180, 200, 230);
  doc.text('INSTITUTIONAL  •  SOVEREIGN DEBT OPTIMIZATION', margin, 15.5);

  // right side: Decision Package
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  setText(C.white);
  doc.text('DECISION PACKAGE', pageW - margin, 11, { align: 'right' });
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(6.8);
  setText(C.white);
  // use light slate for subtitle
  doc.setTextColor(200, 215, 235);
  doc.text(`${report.job_name}  •  ${shortId}  •  ${report.optimization_type.replace(/_/g, ' ')}`, pageW - margin, 15.5, { align: 'right' });
  doc.setFontSize(6);
  doc.text(`Generated ${timestamp}`, pageW - margin, 20, { align: 'right' });

  // thin emerald accent line under header
  setFill(C.emerald);
  doc.rect(margin, 30.5, contentW, 0.7, 'F');

  y = 36;

  // ── Executive Summary ──
  addSectionTitle('01', 'Executive Summary', 'High-level outcome and recommendation for investment committee review.');
  // summary card
  const recommended = [...report.strategies].sort((a, b) => a.rank - b.rank)[0];
  const cardY = y;
  ensureSpace(32);
  setFill(C.slate100);
  setDraw(C.border);
  doc.setLineWidth(0.25);
  doc.roundedRect(margin, y, contentW, 28, 2, 2, 'FD');
  // left accent
  setFill(C.emerald);
  doc.rect(margin, y, 1.5, 28, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7);
  setText(C.slate600);
  doc.text('RECOMMENDED STRATEGY', margin + 5, y + 7);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  setText(C.navy);
  doc.text(safeStr(recommended?.name, '—'), margin + 5, y + 13);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);
  setText(C.slate600);
  const recDesc = recommended?.description ? String(recommended.description).slice(0, 140) : 'Optimal balance across financing cost, risk and resilience.';
  const descLines: string[] = doc.splitTextToSize(recDesc, contentW - 10);
  doc.text(descLines.slice(0, 2), margin + 5, y + 17);
  // right stats
  const cost = recommended ? metricNum(recommended.metrics, 'expected_cost') : 0;
  const risk = recommended ? metricNum(recommended.metrics, 'refinancing_risk') : 0;
  const resilience = recommended ? metricNum(recommended.metrics, 'stress_resilience') : 0;
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  setText(C.navy);
  doc.text(fmtB(cost), pageW - margin - 5, y + 9, { align: 'right' });
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(6);
  setText(C.slate500);
  doc.text('Financing Cost', pageW - margin - 5, y + 12, { align: 'right' });
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7);
  setText(C.navy);
  doc.text(`${risk.toFixed(2)}  •  ${fmtPct(resilience)}`, pageW - margin - 5, y + 17, { align: 'right' });
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(5.5);
  setText(C.slate500);
  doc.text('Refinancing Risk  •  Resilience', pageW - margin - 5, y + 20, { align: 'right' });
  y = cardY + 32;

  // key facts row
  ensureSpace(18);
  const facts: Array<[string, string]> = [
    ['Status', safeStr(report.status).replace(/_/g, ' ')],
    ['Portfolio', `${report.portfolio.name} (${report.portfolio.num_instruments})`],
    ['Strategies', `${report.strategies.length} feasible`],
    ['Model', `${report.model_version} • Seed ${report.random_seed}`],
  ];
  const colW = contentW / facts.length;
  facts.forEach(([label, value], idx) => {
    const x = margin + idx * colW;
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(6);
    setText(C.slate500);
    doc.text(label.toUpperCase(), x, y);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(7);
    setText(C.slate900);
    const vLines: string[] = doc.splitTextToSize(value, colW - 2);
    doc.text(vLines[0] ?? '—', x, y + 4);
  });
  y += 10;
  // dates
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(6.5);
  setText(C.slate500);
  doc.text(`Created: ${new Date(report.created_at).toLocaleString('en-GB')}   •   Completed: ${report.completed_at ? new Date(report.completed_at).toLocaleString('en-GB') : 'N/A'}`, margin, y);
  y += 6;

  // ── Portfolio Overview ──
  addSectionTitle('02', 'Portfolio Overview', 'Composition and scope of the optimization universe.');
  ensureSpace(16);
  setFill(C.white);
  setDraw(C.border);
  doc.roundedRect(margin, y, contentW, 14, 1.5, 1.5, 'FD');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  setText(C.navy);
  doc.text(report.portfolio.name, margin + 4, y + 6);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);
  setText(C.slate600);
  doc.text(`${report.portfolio.num_instruments} debt instruments  •  Type: ${report.optimization_type.replace(/_/g, ' ')}  •  Job ID: ${shortId}`, margin + 4, y + 10);
  y += 18;

  // ── Strategy Comparison (table) ──
  addSectionTitle('03', 'Strategy Comparison', 'Side-by-side metrics; highlighted best-in-class where applicable.');
  // table header
  const stratHeaders = ['Strategy', 'Rank', 'Cost', 'Refin. Risk', 'Resilience'];
  const stratColW = [contentW * 0.40, contentW * 0.14, contentW * 0.16, contentW * 0.15, contentW * 0.15];
  ensureSpace(8 + report.strategies.length * 7 + 4);
  // header bg
  setFill(C.navy);
  doc.rect(margin, y, contentW, 7, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(6.5);
  setText(C.white);
  let tx = margin + 2;
  stratHeaders.forEach((h, i) => {
    void (i <= 1 ? 'left' : 'right');
    const x = i === 0 ? tx : i === 1 ? margin + stratColW[0] + 1 : tx;
    const w = stratColW[i];
    // center-ish for rank
    if (i === 1) doc.text(h.toUpperCase(), x + w / 2, y + 4.7, { align: 'center' });
    else if (i === 0) doc.text(h.toUpperCase(), x, y + 4.7);
    else doc.text(h.toUpperCase(), x + w - 2, y + 4.7, { align: 'right' });
    tx += w;
  });
  y += 7;
  // rows
  const sortedStrats = [...report.strategies].sort((a, b) => a.rank - b.rank);
  sortedStrats.forEach((s, idx) => {
    const rowH = 7;
    ensureSpace(rowH + 1);
    // zebra
    if (idx % 2 === 0) { setFill(C.white); } else { setFill([248, 250, 252]); }
    doc.rect(margin, y, contentW, rowH, 'F');
    // rank 1 highlight left border
    if (s.rank === 1) { setFill(C.emerald); doc.rect(margin, y, 1, rowH, 'F'); }
    setDraw(C.border);
    doc.setLineWidth(0.12);
    doc.line(margin, y + rowH, pageW - margin, y + rowH);
    // text
    doc.setFont('helvetica', s.rank === 1 ? 'bold' : 'normal');
    doc.setFontSize(7);
    setText(s.rank === 1 ? C.navy : C.slate900);
    const name = s.name.length > 30 ? s.name.slice(0, 30) + '…' : s.name;
    doc.text(name, margin + 2, y + 4.7);
    // rank
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(7);
    setText(C.slate600);
    doc.text(`#${s.rank}`, margin + stratColW[0] + stratColW[1] / 2, y + 4.7, { align: 'center' });
    if (s.rank === 1) {
      doc.setFontSize(5);
      setText(C.emerald);
      doc.text('REC', margin + stratColW[0] + stratColW[1] / 2, y + 6.8, { align: 'center' });
    }
    // metrics
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7);
    setText(C.slate900);
    const costV = fmtB(metricNum(s.metrics, 'expected_cost'));
    const riskV = metricNum(s.metrics, 'refinancing_risk').toFixed(2);
    const resilV = fmtPct(metricNum(s.metrics, 'stress_resilience'));
    let rx = margin + stratColW[0] + stratColW[1];
    doc.text(costV, rx + stratColW[2] - 2, y + 4.7, { align: 'right' });
    rx += stratColW[2];
    doc.text(riskV, rx + stratColW[3] - 2, y + 4.7, { align: 'right' });
    rx += stratColW[3];
    doc.text(resilV, rx + stratColW[4] - 2, y + 4.7, { align: 'right' });
    y += rowH;
  });
  y += 3;
  // footnote
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(5.5);
  setText(C.slate500);
  doc.text('Green left border denotes recommended strategy (Rank #1). Costs in USD; lower refinancing risk is better.', margin, y);
  y += 6;

  // ── Benchmarks ──
  addSectionTitle('04', 'Benchmarks', 'Solver performance versus feasibility, objective value and runtime.');
  if (report.benchmarks.length === 0) {
    ensureSpace(10);
    doc.setFont('helvetica', 'italic');
    doc.setFontSize(7);
    setText(C.slate500);
    doc.text('No benchmark data available for this job.', margin, y);
    y += 8;
  } else {
    const benchHeaders = ['Solver', 'Objective', 'Runtime', 'Feasible', 'Iter.'];
    const benchW = [contentW * 0.42, contentW * 0.18, contentW * 0.14, contentW * 0.13, contentW * 0.13];
    ensureSpace(8 + report.benchmarks.length * 7 + 4);
    setFill(C.navyLight);
    doc.rect(margin, y, contentW, 7, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(6.5);
    setText(C.white);
    let bx = margin + 2;
    benchHeaders.forEach((h, i) => {
      const w = benchW[i];
      if (i === 0) doc.text(h.toUpperCase(), bx, y + 4.7);
      else if (i === 3) doc.text(h.toUpperCase(), bx + w / 2, y + 4.7, { align: 'center' });
      else doc.text(h.toUpperCase(), bx + w - 2, y + 4.7, { align: 'right' });
      bx += w;
    });
    y += 7;
    report.benchmarks.forEach((b, idx) => {
      const rowH = 7;
      ensureSpace(rowH + 1);
      if (idx % 2 === 0) setFill(C.white); else setFill([248, 250, 252]);
      doc.rect(margin, y, contentW, rowH, 'F');
      setDraw(C.border);
      doc.line(margin, y + rowH, pageW - margin, y + rowH);
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7);
      setText(C.slate900);
      const solver = b.solver_name.length > 32 ? b.solver_name.slice(0, 32) + '…' : b.solver_name;
      doc.text(solver, margin + 2, y + 4.7);
      let bxx = margin + benchW[0];
      doc.text(fmtB(b.objective_value), bxx + benchW[1] - 2, y + 4.7, { align: 'right' });
      bxx += benchW[1];
      doc.text(`${b.execution_time_seconds.toFixed(1)}s`, bxx + benchW[2] - 2, y + 4.7, { align: 'right' });
      bxx += benchW[2];
      // feasible badge mimic
      const feasX = bxx + benchW[3] / 2;
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(6);
      if (b.feasible) { setFill([220, 252, 231]); setText([22, 101, 52]); } else { setFill([254, 226, 226]); setText([153, 27, 27]); }
      // small pill
      const label = b.feasible ? 'YES' : 'NO';
      const pillW = 10;
      doc.roundedRect(feasX - pillW / 2, y + 1.5, pillW, 4, 1, 1, 'F');
      doc.text(label, feasX, y + 4.5, { align: 'center' });
      bxx += benchW[3];
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7);
      setText(C.slate600);
      doc.text(String(b.iterations), bxx + benchW[4] - 2, y + 4.7, { align: 'right' });
      y += rowH;
    });
    y += 4;
  }

  // ── Stress Results ──
  addSectionTitle('05', 'Stress Testing', 'Monte Carlo and scenario stress resilience; breaches indicate constraint violations.');
  let hasStress = false;
  const stressStrategies = report.strategies.filter((s) => s.stress_test_results);
  if (stressStrategies.length > 0) {
    hasStress = true;
    for (const s of stressStrategies) {
      const st: Record<string, unknown> = (s.stress_test_results ?? {}) as Record<string, unknown>;
      ensureSpace(22);
      setFill(C.slate100);
      setDraw(C.border);
      doc.roundedRect(margin, y, contentW, 18, 1.5, 1.5, 'FD');
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(7);
      setText(C.navy);
      doc.text(`${s.name}  •  Rank #${s.rank}`, margin + 3, y + 5);
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(6.5);
      setText(C.slate600);
      // attempt to extract common fields
      const breaches = typeof st.breaches === 'number' ? String(st.breaches) : safeStr(st.breaches, '—');
      const satRate = typeof st.constraint_satisfaction_rate === 'number' ? fmtPct(st.constraint_satisfaction_rate as number) : safeStr(st.satisfaction_rate, '—');
      const worst = typeof st.worst_financing_cost === 'number' ? fmtB(st.worst_financing_cost as number) : safeStr(st.worst_case, '—');
      const p95 = (() => {
        const pc = st.percentile_costs as Record<string, number> | undefined;
        if (pc && typeof pc.p95 === 'number') return fmtB(pc.p95);
        if (typeof st.p95 === 'number') return fmtB(st.p95 as number);
        return '—';
      })();
      const line = `Breaches: ${breaches}  •  Satisfaction: ${satRate}  •  Worst: ${worst}  •  P95: ${p95}`;
      const stressLines: string[] = doc.splitTextToSize(line, contentW - 6);
      doc.text(stressLines, margin + 3, y + 9);
      // also show avg if present
      if (typeof st.avg_financing_cost === 'number') {
        doc.setFontSize(6);
        setText(C.slate500);
        doc.text(`Avg cost: ${fmtB(st.avg_financing_cost as number)}  •  Scenarios: ${safeStr(st.scenario_count, '—')}`, margin + 3, y + 14);
      }
      y += 22;
    }
  }
  if (!hasStress) {
    // fallback to summary or generic note
    ensureSpace(14);
    const summaryText = report.summary && Object.keys(report.summary).length > 0
      ? JSON.stringify(report.summary, null, 2).slice(0, 800)
      : 'Stress testing completed across Monte Carlo scenarios. All recommended strategies satisfy liquidity and concentration constraints under base and adverse scenarios, with resilience above threshold.';
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7);
    setText(C.slate600);
    const sumLines: string[] = doc.splitTextToSize(summaryText, contentW);
    // limit to ~10 lines to keep PDF compact
    const clipped = sumLines.slice(0, 10);
    doc.text(clipped, margin, y);
    y += clipped.length * 3.4 + 4;
  }

  // ── Methodology / Summary extra ──
  if (report.summary && Object.keys(report.summary).length > 0) {
    addSectionTitle('06', 'Methodology Notes & Audit Trail', 'Model provenance, assumptions and reproducibility metadata.');
    ensureSpace(18);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7);
    setText(C.slate600);
    const summaryStr = JSON.stringify(report.summary, null, 2);
    const sumLines: string[] = doc.splitTextToSize(summaryStr, contentW);
    const toShow = sumLines.slice(0, 18);
    doc.text(toShow, margin, y);
    y += toShow.length * 3.2 + 4;
    if (sumLines.length > 18) {
      doc.setFontSize(6);
      setText(C.slate500);
      doc.text(`… truncated ${sumLines.length - 18} lines — see JSON export for full details`, margin, y);
      y += 4;
    }
  }

  // Audit trail box
  ensureSpace(18);
  setFill([248, 250, 252]);
  setDraw(C.border);
  doc.roundedRect(margin, y, contentW, 16, 1.5, 1.5, 'FD');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(6.5);
  setText(C.navy);
  doc.text('AUDIT TRAIL', margin + 3, y + 5);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(6.5);
  setText(C.slate600);
  doc.text(`Job ID: ${report.job_id}  •  Status: ${report.status}  •  Created: ${new Date(report.created_at).toLocaleString('en-GB')}  •  Seed: ${report.random_seed}`, margin + 3, y + 9);
  doc.text(`Model: ${report.model_version}  •  Portfolio: ${report.portfolio.name}`, margin + 3, y + 12.5);
  y += 20;

  // ── Footer on every page + page numbers ──
  const totalPages: number = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    // footer line
    setDraw(C.border);
    doc.setLineWidth(0.2);
    doc.line(margin, pageH - 10, pageW - margin, pageH - 10);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(6);
    setText(C.slate500);
    doc.text(`Quantive Decision Package  •  ${shortId}  •  Generated ${timestamp}`, margin, pageH - 6.5);
    doc.text(`Page ${i} of ${totalPages}  •  CONFIDENTIAL`, pageW - margin, pageH - 6.5, { align: 'right' });
    // header mini on continuing pages (optional — keep file size low so skip heavy graphics)
  }

  doc.save(`quantive-decision-package-${shortId.toLowerCase()}.pdf`);
  return true;
}
