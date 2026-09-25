import { useEffect, useState } from 'react';
import { personalApi } from '../api';
import { Shield, AlertTriangle, CheckCircle, FileText, Clock, ExternalLink } from 'lucide-react';

export default function CompliancePage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    personalApi.complianceStatus().then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-zinc-400">Loading compliance status...</div>;
  if (!data) return <div className="p-8 text-zinc-500">Unable to load compliance data. Connect a bank account to get started.</div>;

  const { score, analysis, alerts, uncategorized_txns } = data;
  const scoreColor = score >= 80 ? 'text-emerald-400' : score >= 50 ? 'text-sky-400' : 'text-red-400';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Compliance Monitoring</h1>
        <p className="text-zinc-400 mt-1">Real-time tax compliance status and alerts</p>
      </div>

      {/* Compliance Score */}
      <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Compliance Score</h2>
            <p className="text-zinc-400 text-sm">Based on withholding, documents, and filing status</p>
          </div>
          <div className={`text-5xl font-bold ${scoreColor}`}>{score}</div>
        </div>
        <div className="mt-4 h-2 bg-zinc-800 rounded-full overflow-hidden">
          <div className={`h-full rounded-full transition-all ${score >= 80 ? 'bg-emerald-500' : score >= 50 ? 'bg-sky-500' : 'bg-red-500'}`}
               style={{ width: `${score}%` }} />
        </div>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-white">Active Alerts</h2>
          {alerts.map((alert: any) => (
            <div key={alert.id}
                 className={`bg-zinc-900 rounded-lg border p-4 flex items-start gap-3 ${
                   alert.severity === 'critical' ? 'border-red-800' :
                   alert.severity === 'warning' ? 'border-sky-800' : 'border-zinc-800'
                 }`}>
              {alert.severity === 'critical' ? <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5" /> :
               alert.severity === 'warning' ? <AlertTriangle className="w-5 h-5 text-sky-400 mt-0.5" /> :
               <Shield className="w-5 h-5 text-blue-400 mt-0.5" />}
              <div className="flex-1">
                <h3 className="font-medium text-white">{alert.title}</h3>
                <p className="text-zinc-400 text-sm mt-1">{alert.description}</p>
                {alert.amount > 0 && (
                  <p className="text-zinc-300 text-sm mt-1 font-medium">
                    Amount: ${(alert.amount / 100).toLocaleString()}
                  </p>
                )}
                {alert.due_date && (
                  <p className="text-sky-400 text-sm mt-1 flex items-center gap-1">
                    <Clock className="w-3 h-3" /> Due: {alert.due_date}
                  </p>
                )}
              </div>
              {!alert.acknowledged && (
                <button onClick={() => personalApi.acknowledgeAlert(alert.id).then(() => window.location.reload())}
                        className="text-zinc-500 hover:text-zinc-300 text-sm">
                  Dismiss
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Withholding Analysis */}
      <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Withholding Analysis</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-zinc-400 text-sm">YTD Income</p>
            <p className="text-white text-xl font-semibold">${(analysis.ytd_income / 100).toLocaleString()}</p>
          </div>
          <div>
            <p className="text-zinc-400 text-sm">YTD Withholding</p>
            <p className="text-white text-xl font-semibold">${(analysis.ytd_withholding / 100).toLocaleString()}</p>
          </div>
          <div>
            <p className="text-zinc-400 text-sm">Projected Tax</p>
            <p className="text-white text-xl font-semibold">${(analysis.projected_total_tax / 100).toLocaleString()}</p>
          </div>
          <div>
            <p className="text-zinc-400 text-sm">Shortfall</p>
            <p className={`text-xl font-semibold ${analysis.shortfall > 0 ? 'text-sky-400' : 'text-emerald-400'}`}>
              {analysis.shortfall > 0 ? `$${(analysis.shortfall / 100).toLocaleString()}` : 'None'}
            </p>
          </div>
        </div>

        {analysis.shortfall > 0 && (
          <div className="mt-4 bg-sky-950/30 border border-sky-800 rounded-lg p-4">
            <p className="text-sky-200 text-sm">
              <strong>Quarterly payment needed:</strong> ${(analysis.quarterly_payment_needed / 100).toLocaleString()} × {analysis.remaining_quarters} remaining quarters
            </p>
          </div>
        )}

        <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-zinc-400">Tax Bracket</p>
            <p className="text-white font-medium">{analysis.bracket || 'N/A'}</p>
          </div>
          <div>
            <p className="text-zinc-400">Marginal Rate</p>
            <p className="text-white font-medium">{analysis.marginal_rate ? `${(analysis.marginal_rate * 100).toFixed(0)}%` : 'N/A'}</p>
          </div>
          <div>
            <p className="text-zinc-400">Filing Status</p>
            <p className="text-white font-medium capitalize">{analysis.filing_status}</p>
          </div>
        </div>
      </div>

      {/* Uncategorized Transactions */}
      {uncategorized_txns > 0 && (
        <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4 flex items-center gap-3">
          <FileText className="w-5 h-5 text-sky-400" />
          <div className="flex-1">
            <p className="text-white">{uncategorized_txns} transactions need tax categorization review</p>
            <p className="text-zinc-400 text-sm">Review these transactions to improve tax tracking accuracy</p>
          </div>
          <a href="/personal/transactions" className="text-sky-400 hover:text-sky-300 text-sm flex items-center gap-1">
            Review <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      )}

      {/* Filing Calendar */}
      <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">2026 Filing Calendar</h2>
        <div className="space-y-3">
          {[
            { date: 'Jan 15', label: 'Q4 2025 Estimated Tax Due', status: 'past' },
            { date: 'Apr 15', label: 'Tax Return Filing Deadline', status: 'upcoming' },
            { date: 'Apr 15', label: 'Q1 2026 Estimated Tax Due', status: 'upcoming' },
            { date: 'Jun 15', label: 'Q2 2026 Estimated Tax Due', status: 'future' },
            { date: 'Sep 15', label: 'Q3 2026 Estimated Tax Due', status: 'future' },
            { date: 'Oct 15', label: 'Extended Return Deadline', status: 'future' },
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className={`w-2 h-2 rounded-full ${
                item.status === 'past' ? 'bg-zinc-600' :
                item.status === 'upcoming' ? 'bg-sky-500' : 'bg-zinc-700'
              }`} />
              <span className="text-zinc-400 text-sm w-20">{item.date}</span>
              <span className={`text-sm ${item.status === 'past' ? 'text-zinc-500' : 'text-white'}`}>{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
