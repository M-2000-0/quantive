import { useEffect, useState } from "react";
import { api } from "../api/client";

export function AlertsPage() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    setLoading(true);
    api.get(`/alerts?limit=50&sortBy=createdAt${filter ? `&status=${filter}` : ""}`).then((res) => {
      if (res?.success) setAlerts(res.data || []);
      setLoading(false);
    });
  }, [filter]);

  async function dismissAlert(id: string) {
    const res = await api.patch(`/alerts/${id}/status`, { status: "DISMISSED" });
    if (res?.success) setAlerts(alerts.map((a) => a.id === id ? { ...a, status: "DISMISSED" } : a));
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-on-surface">Alerts</h2>
          <p className="text-xs text-on-muted mt-0.5">Manage and review compliance alerts</p>
        </div>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="text-xs bg-surface-container border border-surface-variant rounded px-2 py-1.5 text-on-surface"
        >
          <option value="">All status</option>
          <option value="OPEN">Open</option>
          <option value="ACKNOWLEDGED">Acknowledged</option>
          <option value="DISMISSED">Dismissed</option>
        </select>
      </div>

      <div className="space-y-2">
        {loading ? (
          <p className="text-sm text-on-muted p-6 text-center">Loading...</p>
        ) : alerts.length === 0 ? (
          <p className="text-sm text-on-muted p-6 text-center">No alerts match your filter.</p>
        ) : alerts.map((alert) => (
          <div key={alert.id} className="bg-surface-container border border-surface-variant rounded-lg p-4 flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                  alert.severity === "CRITICAL" ? "bg-error/20 text-error" :
                  alert.severity === "HIGH" ? "bg-error/10 text-error" :
                  alert.severity === "MEDIUM" ? "bg-primary/20 text-primary" :
                  "bg-surface-variant text-on-muted"
                }`}>{alert.severity}</span>
                <span className={`text-[10px] uppercase tracking-wider ${
                  alert.status === "OPEN" ? "text-error" : alert.status === "DISMISSED" ? "text-on-muted" : "text-primary"
                }`}>{alert.status}</span>
              </div>
              <p className="text-sm text-on-surface font-medium">{alert.title}</p>
              <p className="text-xs text-on-muted mt-0.5 line-clamp-2">{alert.description}</p>
              {alert.reasonCode && <p className="text-[10px] text-on-variant mt-1 font-mono">Reason: {alert.reasonCode}</p>}
            </div>
            {alert.status !== "DISMISSED" && alert.status !== "ESCALATED" && (
              <button onClick={() => dismissAlert(alert.id)} className="text-xs text-on-muted border border-surface-variant rounded px-2 py-1 hover:bg-surface-high shrink-0">
                Dismiss
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
