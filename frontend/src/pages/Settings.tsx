import { useEffect, useState } from "react";
import { api } from "../api/client";

export function SettingsPage() {
  const [onboarding, setOnboarding] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoResult, setDemoResult] = useState<any>(null);

  useEffect(() => {
    api.get("/admin/onboarding").then((res) => {
      if (res?.success) setOnboarding(res.data);
      setLoading(false);
    });
  }, []);

  async function loadDemoData() {
    setDemoLoading(true);
    const res = await api.post("/demo/generate");
    if (res?.success) setDemoResult(res.data);
    setDemoLoading(false);
  }

  if (loading) return <div className="text-on-muted text-sm p-8">Loading...</div>;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-on-surface">Settings</h2>
        <p className="text-xs text-on-muted mt-0.5">Organization configuration</p>
      </div>

      {onboarding && (
        <div className="bg-surface-container border border-surface-variant rounded-lg p-4">
          <h3 className="text-sm font-medium text-on-surface mb-3">Getting Started</h3>
          <div className="mb-3">
            <div className="flex items-center justify-between text-xs text-on-muted mb-1">
              <span>Setup progress</span>
              <span>{onboarding.progress}%</span>
            </div>
            <div className="h-1.5 bg-surface-variant rounded-full overflow-hidden">
              <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${onboarding.progress}%` }}></div>
            </div>
          </div>
          <div className="space-y-2">
            {onboarding.steps?.map((step: any) => (
              <div key={step.id} className="flex items-center gap-3 text-xs">
                <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[8px] font-bold ${
                  step.done ? "bg-primary text-black" : "bg-surface-variant text-on-muted"
                }`}>{step.done ? "\u2713" : step.id === "connect_data" ? "!" : ""}</span>
                <span className={step.done ? "text-on-surface" : "text-on-muted"}>{step.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-surface-container border border-surface-variant rounded-lg p-4">
        <h3 className="text-sm font-medium text-on-surface mb-2">Demo Data</h3>
        <p className="text-xs text-on-muted mb-3">Populate your workspace with realistic sample data to explore the platform.</p>
        <button
          onClick={loadDemoData}
          disabled={demoLoading}
          className="text-xs bg-primary text-black font-semibold px-4 py-2 rounded hover:brightness-110 transition-all disabled:opacity-60"
        >
          {demoLoading ? "Generating..." : "Load Demo Data"}
        </button>
        {demoResult && (
          <div className="mt-3 text-xs text-on-variant space-y-0.5">
            <p>Generated: {demoResult.transactions} transactions, {demoResult.alerts} alerts, {demoResult.cases} cases</p>
          </div>
        )}
      </div>

      <div className="bg-surface-container border border-surface-variant rounded-lg p-4">
        <h3 className="text-sm font-medium text-on-surface mb-2">Blockchain Integration</h3>
        <p className="text-xs text-on-muted mb-3">Connect your blockchain data source to start monitoring in real time.</p>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-surface border border-surface-variant rounded text-xs">
            <div>
              <p className="text-on-surface font-medium">Etherscan</p>
              <p className="text-on-muted">Ethereum mainnet</p>
            </div>
            <span className="text-on-muted text-[10px]">Coming soon</span>
          </div>
          <div className="flex items-center justify-between p-3 bg-surface border border-surface-variant rounded text-xs">
            <div>
              <p className="text-on-surface font-medium">Alchemy</p>
              <p className="text-on-muted">Multi-chain support</p>
            </div>
            <span className="text-on-muted text-[10px]">Coming soon</span>
          </div>
        </div>
      </div>
    </div>
  );
}
