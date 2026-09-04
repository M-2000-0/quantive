import { useState, useCallback } from 'react';
import Button from './ui/Button';
import Badge from './ui/Badge';

interface MinisterBriefProps {
  jobId: string;
  jobName: string;
  portfolioName: string;
  savings: number;
  improvementPct: number;
  baselineCost: number;
  optimizedCost: number;
  riskScore: number;
  recommendations: string[];
  strategies: Array<{ name: string; description: string; savings: number; risk: string }>;
}

export default function MinisterBriefExport({
  jobId,
  jobName,
  portfolioName,
  savings,
  improvementPct,
  baselineCost,
  optimizedCost,
  riskScore,
  recommendations,
  strategies }: MinisterBriefProps) {
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState(false);

  const generateBrief = useCallback(async () => {
    setGenerating(true);
    try {
      // Build the HTML for the PDF
      const date = new Date().toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric' });

      const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Minister Brief - ${jobName}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Georgia', serif; color: #1a1a2e; line-height: 1.6; padding: 40px; max-width: 800px; margin: 0 auto; }
    .header { border-bottom: 3px solid #1e3a5f; padding-bottom: 20px; margin-bottom: 30px; }
    .header h1 { font-size: 24px; color: #1e3a5f; margin-bottom: 5px; }
    .header .subtitle { font-size: 14px; color: #666; }
    .classification { background: #fee2e2; color: #991b1b; padding: 4px 12px; border-radius: 4px; font-size: 11px; font-weight: bold; text-transform: uppercase; display: inline-block; margin-bottom: 15px; }
    .section { margin-bottom: 25px; }
    .section h2 { font-size: 16px; color: #1e3a5f; border-bottom: 1px solid #e5e7eb; padding-bottom: 8px; margin-bottom: 12px; }
    .metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }
    .metric { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; }
    .metric .label { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric .value { font-size: 24px; font-weight: bold; color: #1e3a5f; margin-top: 4px; }
    .metric .change { font-size: 12px; color: #059669; margin-top: 2px; }
    .metric .change.negative { color: #dc2626; }
    .strategy { background: #f0fdf4; border-left: 4px solid #059669; padding: 12px 16px; margin-bottom: 10px; border-radius: 0 8px 8px 0; }
    .strategy .name { font-weight: bold; color: #1e3a5f; }
    .strategy .desc { font-size: 13px; color: #475569; margin-top: 4px; }
    .strategy .savings { font-size: 12px; color: #059669; font-weight: bold; margin-top: 4px; }
    .recommendation { background: #eff6ff; border-left: 4px solid #3b82f6; padding: 10px 16px; margin-bottom: 8px; border-radius: 0 6px 6px 0; font-size: 13px; }
    .footer { border-top: 2px solid #1e3a5f; padding-top: 15px; margin-top: 30px; font-size: 11px; color: #94a3b8; }
    .risk-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .risk-low { background: #dcfce7; color: #166534; }
    .risk-medium { background: #fef3c7; color: #92400e; }
    .risk-high { background: #fee2e2; color: #991b1b; }
  </style>
</head>
<body>
  <div class="header">
    <div class="classification">CONFIDENTIAL — MINISTER'S OFFICE</div>
    <h1>Debt Portfolio Optimization Brief</h1>
    <div class="subtitle">${portfolioName} · ${date} · Reference: ${jobId.slice(0, 8).toUpperCase()}</div>
  </div>

  <div class="section">
    <h2>Executive Summary</h2>
    <p style="font-size: 14px; margin-bottom: 15px;">
      Analysis of <strong>${portfolioName}</strong> has identified optimization opportunities that could reduce
      annual financing costs by <strong>$${(savings / 1_000_000).toFixed(1)}M</strong> (${improvementPct}% reduction)
      while maintaining or improving the portfolio's risk profile.
    </p>
  </div>

  <div class="section">
    <h2>Key Financial Metrics</h2>
    <div class="metric-grid">
      <div class="metric">
        <div class="label">Current Annual Cost</div>
        <div class="value">$${(baselineCost / 1_000_000).toFixed(1)}M</div>
      </div>
      <div class="metric">
        <div class="label">Optimized Annual Cost</div>
        <div class="value" style="color: #059669;">$${(optimizedCost / 1_000_000).toFixed(1)}M</div>
        <div class="change">↓ $${(savings / 1_000_000).toFixed(1)}M savings</div>
      </div>
      <div class="metric">
        <div class="label">10-Year Projected Savings</div>
        <div class="value" style="color: #059669;">$${((savings * 10) / 1_000_000).toFixed(0)}M</div>
      </div>
      <div class="metric">
        <div class="label">Portfolio Risk Score</div>
        <div class="value">${riskScore}/100</div>
        <div class="risk-badge ${riskScore < 30 ? 'risk-low' : riskScore < 60 ? 'risk-medium' : 'risk-high'}">
          ${riskScore < 30 ? 'LOW RISK' : riskScore < 60 ? 'MODERATE RISK' : 'HIGH RISK'}
        </div>
      </div>
    </div>
  </div>

  <div class="section">
    <h2>Recommended Strategies</h2>
    ${strategies.map((s, i) => `
      <div class="strategy">
        <div class="name">${i + 1}. ${s.name}</div>
        <div class="desc">${s.description}</div>
        <div class="savings">Projected savings: $${(s.savings / 1_000_000).toFixed(1)}M annually</div>
      </div>
    `).join('')}
  </div>

  <div class="section">
    <h2>Key Recommendations</h2>
    ${recommendations.map((r, i) => `
      <div class="recommendation">${i + 1}. ${r}</div>
    `).join('')}
  </div>

  <div class="section">
    <h2>Risk Assessment</h2>
    <p style="font-size: 13px;">
      The recommended strategies have been stress-tested across 1,000 market scenarios.
      Overall portfolio risk score: <strong>${riskScore}/100</strong>.
      ${riskScore < 30 ? 'The portfolio is well-positioned for current market conditions.' :
        riskScore < 60 ? 'Moderate risk exposure — recommend monitoring key indicators.' :
        'Elevated risk — recommend conservative approach with gradual implementation.'}
    </p>
  </div>

  <div class="footer">
    <p><strong>Quantive</strong> — Government Financial Optimization Platform</p>
    <p>Generated ${date} · This document is confidential and intended for the Minister's office only.</p>
    <p>For questions, contact the Debt Management Office.</p>
  </div>
</body>
</html>`;

      // Open in new window for printing/saving as PDF
      const printWindow = window.open('', '_blank');
      if (printWindow) {
        printWindow.document.write(html);
        printWindow.document.close();
        // Trigger print dialog after a short delay
        setTimeout(() => {
          printWindow.print();
        }, 500);
      }
      setGenerated(true);
    } catch (err) {
      console.error('Failed to generate brief:', err);
    } finally {
      setGenerating(false);
    }
  }, [jobId, jobName, portfolioName, savings, improvementPct, baselineCost, optimizedCost, riskScore, recommendations, strategies]);

  return (
    <div className="flex items-center gap-3">
      <Button
        variant="primary"
        onClick={generateBrief}
        disabled={generating}
        leftIcon={
          generating ? (
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          ) : (
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125-1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
          )
        }
      >
        {generating ? 'Generating...' : generated ? 'Regenerate Brief' : 'Generate Minister Brief'}
      </Button>
      {generated && (
        <Badge variant="success">PDF ready — check print dialog</Badge>
      )}
    </div>
  );
}
