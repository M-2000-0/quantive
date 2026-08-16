import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Link } from "react-router-dom";

export function DashboardPage() {
  const [data, setData] = useState<any>(null);
  const [txs, setTxs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [onboarding, setOnboarding] = useState<any>(null);

  useEffect(() => {
    Promise.all([
      api.get("/admin/dashboard"),
      api.get("/transactions?limit=5&sortBy=timestamp"),
      api.get("/admin/onboarding"),
    ]).then(([stats, txRes, ob]) => {
      if (stats?.success) setData(stats.data);
      if (txRes?.success) setTxs(txRes.data || []);
      if (ob?.success) setOnboarding(ob.data);
      setLoading(false);
    });
  }, []);

  if (loading) return <div className="text-on-muted text-sm p-8">Loading...</div>;

  const overview = data?.overview || {};
  const kpis = [
    { label: "Total Transactions", value: (overview.totalTransactions || 0).toLocaleString(), color: "text-primary" },
    { label: "Open Alerts", value: overview.openAlerts || 0, color: "text-error" },
    { label: "Active Cases", value: overview.activeCases || 0, color: "text-on-surface" },
    { label: "Total Wallets", value: (overview.totalWallets || 0).toLocaleString(), color: "text-primary" },
  ];

  const showOnboarding = onboarding && !onboarding.complete && onboarding.progress < 100;

  return (
    <div className="space-y-6">
      {showOnboarding && (
        <div className="bg-surface-container border border-surface-variant rounded-lg p-4 flex items-center justify-between">
          <div>
            <p className="text-sm text-on-surface font-medium">Getting started</p>
            <p className="text-xs text-on-muted mt-0.5">{onboarding.progress}% complete — {onboarding.steps.filter((s: any) => !s.done).length} steps remaining</p>
          </div>
          <Link to="/settings" className="text-xs text-primary hover:underline">Continue setup</Link>
        </div>
      )}

      <div>
        <h2 className="text-lg font-semibold text-on-surface">System Overview</h2>
        <p className="text-xs text-on-muted mt-0.5">Real-time risk telemetry and compliance monitoring.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="bg-surface-container border border-surface-variant rounded-lg p-4">
            <p className="text-xs text-on-muted uppercase tracking-wider">{kpi.label}</p>
            <p className={`text-2xl font-bold mt-1 ${kpi.color}`}>{kpi.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="bg-surface-container border border-surface-variant rounded-lg p-4">
          <h3 className="text-sm font-medium text-on-surface mb-3">Recent Transactions</h3>
          {txs.length === 0 ? (
            <p className="text-xs text-on-muted py-4 text-center">No transactions yet. Connect a data source or load demo data.</p>
          ) : (
            <table className="w-full text-left">
              <thead>
                <tr className="text-[10px] text-on-muted uppercase tracking-wider border-b border-surface-variant/30">
                  <th className="pb-2 font-medium">Hash</th>
                  <th className="pb-2 font-medium">Value</th>
                  <th className="pb-2 font-medium">Risk</th>
                </tr>
              </thead>
              <tbody>
                {txs.map((tx: any) => (
                  <tr key={tx.id} className="border-b border-surface-variant/10 text-xs">
                    <td className="py-2 font-mono text-on-variant">{tx.txHash?.slice(0, 16)}...</td>
                    <td className="py-2">{parseFloat(tx.value).toFixed(4)} {tx.token || "ETH"}</td>
                    <td className="py-2">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                        tx.riskLevel === "CRITICAL" ? "bg-error/20 text-error" :
                        tx.riskLevel === "HIGH" ? "bg-error/10 text-error" :
                        tx.riskLevel === "MEDIUM" ? "bg-primary/20 text-primary" :
                        "bg-surface-variant text-on-muted"
                      }`}>{tx.riskLevel}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="bg-surface-container border border-surface-variant rounded-lg p-4">
          <h3 className="text-sm font-medium text-on-surface mb-3">Alert Severity (30 days)</h3>
          {data?.alertsBySeverity?.length > 0 ? (
            <div className="space-y-3">
              {data.alertsBySeverity.map((a: any) => (
                <div key={a.severity} className="flex items-center justify-between">
                  <span className="text-xs text-on-variant">{a.severity}</span>
                  <div className="flex items-center gap-2">
                    <div className="h-2 rounded bg-surface-variant" style={{ width: 120 }}>
                      <div className={`h-full rounded ${
                        a.severity === "CRITICAL" || a.severity === "HIGH" ? "bg-error" : "bg-primary"
                      }`} style={{ width: `${Math.min(100, a._count * 5)}%` }}></div>
                    </div>
                    <span className="text-xs text-on-surface font-mono">{a._count}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-on-muted py-4 text-center">No alerts in the last 30 days.</p>
          )}
        </div>
      </div>
    </div>
  );
}
