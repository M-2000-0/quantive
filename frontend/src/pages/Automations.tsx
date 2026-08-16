import { useEffect, useState } from "react";
import { api } from "../api/client";

interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  triggerEvent: string;
  icon: string;
  configSchema: Record<string, { label: string; type: string; required: boolean; default?: string }>;
  n8nWorkflowFile: string;
}

const CATEGORIES: Record<string, { label: string; color: string }> = {
  notifications: { label: "Notifications", color: "text-blue-400 border-blue-400/30" },
  ticketing: { label: "Ticketing", color: "text-purple-400 border-purple-400/30" },
  email: { label: "Email", color: "text-green-400 border-green-400/30" },
  onboarding: { label: "Onboarding", color: "text-teal-400 border-teal-400/30" },
  reporting: { label: "Reporting", color: "text-amber-400 border-amber-400/30" },
  ingestion: { label: "Ingestion", color: "text-cyan-400 border-cyan-400/30" },
  compliance: { label: "Compliance", color: "text-rose-400 border-rose-400/30" },
  risk: { label: "Risk Management", color: "text-red-400 border-red-400/30" },
  audit: { label: "Audit & SIEM", color: "text-slate-400 border-slate-400/30" },
  subscription: { label: "Subscription", color: "text-indigo-400 border-indigo-400/30" },
  system: { label: "System Health", color: "text-orange-400 border-orange-400/30" },
  workflow: { label: "Workflow", color: "text-pink-400 border-pink-400/30" },
};

const ICONS: Record<string, string> = {
  slack: "forum", pagerduty: "emergency", teams: "groups", jira: "assignment",
  discord: "chat", email: "mail", sms: "sms", escalation: "trending_up",
  digest: "summarize", demo: "play_arrow", alert: "notifications_active",
  report: "description", csv: "table_chart", blockchain: "hub",
  storage: "cloud", compliance: "verified", risk: "gavel",
  audit: "history", stripe: "credit_card", health: "monitor_heart",
  sso: "fingerprint",
};

export function AutomationsPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [activeIds, setActiveIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    Promise.all([
      api.get("/automations/templates"),
      api.get("/automations/active"),
    ]).then(([tplRes, actRes]) => {
      if (tplRes?.success) setTemplates(tplRes.data || []);
      if (actRes?.success) {
        setActiveIds(new Set(actRes.data.map((a: any) => a.secret)));
      }
      setLoading(false);
    });
  }, []);

  async function toggleAutomation(template: Template) {
    if (activeIds.has(template.id)) {
      const active = await api.get("/automations/active");
      const ep = active?.data?.find((a: any) => a.secret === template.id);
      if (ep) {
        await api.post(`/automations/${ep.id}/deactivate`);
        setActiveIds((prev) => { const next = new Set(prev); next.delete(template.id); return next; });
      }
    } else {
      await api.post("/automations/activate", { templateId: template.id, config: {} });
      setActiveIds((prev) => new Set(prev).add(template.id));
    }
  }

  const categories = [...new Set(templates.map((t) => t.category))];
  const filtered = templates.filter(
    (t) =>
      (!selectedCategory || t.category === selectedCategory) &&
      (!search || t.name.toLowerCase().includes(search.toLowerCase()) || t.description.toLowerCase().includes(search.toLowerCase()))
  );

  const grouped = filtered.reduce<Record<string, Template[]>>((acc, t) => {
    (acc[t.category] = acc[t.category] || []).push(t);
    return acc;
  }, {});

  if (loading) return <div className="text-on-muted text-sm p-8">Loading automations...</div>;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-on-surface">Automations</h2>
        <p className="text-xs text-on-muted mt-0.5">Connect Quantive to n8n for powerful workflow automation across alerts, reporting, compliance, and more.</p>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <input
          type="text"
          placeholder="Search automations..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-surface-container border border-surface-variant rounded-md px-3 py-1.5 text-sm text-on-surface placeholder-on-muted w-64 outline-none focus:border-primary/50"
        />
        <button onClick={() => setSelectedCategory(null)} className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${!selectedCategory ? "bg-primary/20 text-primary border-primary/40" : "text-on-muted border-surface-variant hover:border-on-muted"}`}>All</button>
        {categories.map((cat) => (
          <button key={cat} onClick={() => setSelectedCategory(cat === selectedCategory ? null : cat)} className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${cat === selectedCategory ? "bg-primary/20 text-primary border-primary/40" : "text-on-muted border-surface-variant hover:border-on-muted"}`}>
            {CATEGORIES[cat]?.label || cat}
          </button>
        ))}
      </div>

      {Object.entries(grouped).map(([category, items]) => (
        <div key={category}>
          <h3 className={`text-sm font-semibold uppercase tracking-wider mb-3 ${CATEGORIES[category]?.color?.split(" ")[0] || "text-on-muted"}`}>
            {CATEGORIES[category]?.label || category}
            <span className="text-on-muted ml-2 font-normal normal-case">({items.length})</span>
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {items.map((template) => {
              const active = activeIds.has(template.id);
              return (
                <div key={template.id} className={`bg-surface-container border rounded-lg p-4 transition-all ${active ? "border-primary/40 shadow-sm shadow-primary/5" : "border-surface-variant hover:border-surface-variant/60"}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="material-symbols-outlined text-lg text-primary shrink-0">{ICONS[template.icon] || "bolt"}</span>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-on-surface truncate">{template.name}</p>
                        <p className="text-[10px] text-on-muted uppercase mt-0.5">{template.triggerEvent === "schedule" ? "⏱ Scheduled" : template.triggerEvent === "manual" ? "📋 Manual" : `🔔 On ${template.triggerEvent}`}</p>
                      </div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer shrink-0">
                      <input type="checkbox" className="sr-only peer" checked={active} onChange={() => toggleAutomation(template)} />
                      <div className="w-9 h-5 bg-surface-variant rounded-full peer peer-checked:bg-primary peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all"></div>
                    </label>
                  </div>
                  <p className="text-xs text-on-muted mt-2 line-clamp-2">{template.description}</p>
                  {active && (
                    <div className="mt-2 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-400"></span>
                      <span className="text-[10px] text-green-400 font-medium">Active</span>
                    </div>
                  )}
                  <div className="mt-2 flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[10px] text-on-muted">download</span>
                    <a href={`/api/v1/automations/workflow/${template.id}`} className="text-[10px] text-primary hover:underline" download>
                      Download n8n workflow
                    </a>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}

      <div className="bg-surface-container border border-surface-variant rounded-lg p-4">
        <h3 className="text-sm font-medium text-on-surface mb-2">Connecting to n8n</h3>
        <ol className="text-xs text-on-muted space-y-1.5 list-decimal ml-4">
          <li>Install n8n: <code className="bg-surface-high px-1 rounded text-[10px]">docker run -d --name n8n -p 5678:5678 n8nio/n8n</code></li>
          <li>Import the downloaded workflows into n8n (Workflows → Import from File)</li>
          <li>Configure credentials (Slack webhook, SMTP, PagerDuty, etc.) in n8n</li>
          <li>Copy the n8n webhook URLs and register them in Quantive via the toggle above</li>
          <li>Toggle each automation ON to activate the webhook connection</li>
        </ol>
      </div>
    </div>
  );
}
