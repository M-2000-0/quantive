import { useEffect, useState } from "react";
import { api } from "../api/client";

export function CasesPage() {
  const [cases, setCases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/cases?limit=50&sortBy=createdAt").then((res) => {
      if (res?.success) setCases(res.data || []);
      setLoading(false);
    });
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-on-surface">Cases</h2>
        <p className="text-xs text-on-muted mt-0.5">Investigation workflow management</p>
      </div>

      {loading ? (
        <p className="text-sm text-on-muted p-6 text-center">Loading...</p>
      ) : cases.length === 0 ? (
        <p className="text-sm text-on-muted p-6 text-center">No cases yet. Cases are created from escalated alerts.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {cases.map((c: any) => (
            <div key={c.id} className="bg-surface-container border border-surface-variant rounded-lg p-4 space-y-2">
              <div className="flex items-center gap-2">
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                  c.priority === "CRITICAL" ? "bg-error/20 text-error" :
                  c.priority === "HIGH" ? "bg-error/10 text-error" :
                  c.priority === "MEDIUM" ? "bg-primary/20 text-primary" :
                  "bg-surface-variant text-on-muted"
                }`}>{c.priority}</span>
                <span className={`text-[10px] uppercase tracking-wider ${
                  c.status === "OPEN" ? "text-error" :
                  c.status === "CLOSED" ? "text-on-muted" : "text-primary"
                }`}>{c.status}</span>
              </div>
              <p className="text-sm text-on-surface font-medium">{c.title}</p>
              <p className="text-xs text-on-muted line-clamp-2">{c.description}</p>
              <div className="flex items-center justify-between text-[10px] text-on-muted pt-1">
                <span>{c._count?.alerts || 0} alerts</span>
                <span>{c._count?.comments || 0} comments</span>
              </div>
              {c.assignee && (
                <p className="text-[10px] text-on-variant">Assignee: {c.assignee.name}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
