import { useCallback, useEffect, useState } from 'react';
import { Bot, CheckCircle, Clock, Play, RefreshCw, ShieldAlert, XCircle } from 'lucide-react';
import { api } from '../api';
import type { AgentRun, AgentTool } from '../types';

type RunSummary = { id: string; goal: string; status: string };
const TERMINAL = new Set(['completed', 'failed', 'cancelled']);

const statusColor: Record<string, string> = {
  completed: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-red-100 text-red-700',
  waiting_approval: 'bg-sky-100 text-sky-700',
  running: 'bg-blue-100 text-blue-700',
  queued: 'bg-slate-100 text-slate-600',
  cancelled: 'bg-slate-100 text-slate-500',
};

export default function AgentRunsPage() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [selected, setSelected] = useState<AgentRun | null>(null);
  const [tools, setTools] = useState<AgentTool[]>([]);
  const [loading, setLoading] = useState(true);
  const [goal, setGoal] = useState('');
  const [toolName, setToolName] = useState('');
  const [toolArgs, setToolArgs] = useState('{}');
  const [plan, setPlan] = useState<Array<{ tool: string; args: Record<string, unknown> }>>([]);
  const [comment, setComment] = useState('');
  const [error, setError] = useState('');

  const loadRuns = useCallback(async () => {
    try {
      const data = await api.agent.list();
      setRuns(data.runs);
    } catch (e) {
      console.error('Failed to load runs:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDetail = useCallback(async (id: string) => {
    try {
      const run = await api.agent.get(id);
      setSelected(run);
    } catch (e) {
      console.error('Failed to load run:', e);
    }
  }, []);

  useEffect(() => {
    void loadRuns();
    api.agent.tools().then((d) => {
      setTools(d.tools);
      if (d.tools.length > 0) setToolName(d.tools[0].name);
    }).catch(() => {});
  }, [loadRuns]);

  // Poll the selected run until terminal.
  useEffect(() => {
    if (!selected || TERMINAL.has(selected.status)) return;
    const t = setInterval(() => void loadDetail(selected.id), 2000);
    return () => clearInterval(t);
  }, [selected, loadDetail]);

  const addStep = () => {
    try {
      const args = JSON.parse(toolArgs || '{}');
      setPlan([...plan, { tool: toolName, args }]);
      setError('');
    } catch {
      setError('Step args must be valid JSON');
    }
  };

  const startRun = async () => {
    if (!goal.trim() || plan.length === 0) {
      setError('Goal and at least one step are required');
      return;
    }
    try {
      const run = await api.agent.start({ goal: goal.trim(), steps: plan });
      setGoal('');
      setPlan([]);
      setError('');
      await loadRuns();
      await loadDetail(run.id);
    } catch (e: any) {
      setError(e?.message || 'Failed to start run');
    }
  };

  const decide = async (seq: number, approved: boolean) => {
    if (!selected) return;
    try {
      const run = await api.agent.approve(selected.id, seq, approved, comment);
      setComment('');
      setSelected(run);
      await loadRuns();
    } catch (e: any) {
      setError(e?.message || 'Approval failed (four-eyes: creator cannot approve)');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
              <Bot className="w-8 h-8 text-blue-600" />
              Agent Runs
            </h1>
            <p className="text-slate-600 mt-2">
              Plan → execute → verify, with human approval for sensitive steps.
            </p>
          </div>
          <button
            onClick={() => { void loadRuns(); if (selected) void loadDetail(selected.id); }}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm hover:bg-slate-50"
          >
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Run list + creator */}
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm p-4 border border-slate-200">
              <h2 className="font-semibold text-slate-900 mb-3">New run</h2>
              <input
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="Goal, e.g. Summarize Acme risk"
                className="w-full mb-2 px-3 py-2 border border-slate-200 rounded-lg text-sm"
              />
              <div className="flex gap-2 mb-2">
                <select
                  value={toolName}
                  onChange={(e) => setToolName(e.target.value)}
                  className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-sm"
                >
                  {tools.map((t) => (
                    <option key={t.name} value={t.name}>
                      {t.name} ({t.risk})
                    </option>
                  ))}
                </select>
                <input
                  value={toolArgs}
                  onChange={(e) => setToolArgs(e.target.value)}
                  placeholder='{"portfolio_id":"..."}'
                  className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-sm font-mono"
                />
                <button onClick={addStep} className="px-3 py-2 bg-slate-900 text-white rounded-lg text-sm">
                  Add
                </button>
              </div>
              {plan.length > 0 && (
                <ol className="mb-2 text-sm text-slate-600 list-decimal list-inside">
                  {plan.map((s, i) => (
                    <li key={i} className="font-mono text-xs">{s.tool}</li>
                  ))}
                </ol>
              )}
              <button
                onClick={() => void startRun()}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
              >
                <Play className="w-4 h-4" /> Start run
              </button>
            </div>

            <div className="bg-white rounded-xl shadow-sm p-4 border border-slate-200">
              <h2 className="font-semibold text-slate-900 mb-3">Runs</h2>
              {loading ? (
                <p className="text-sm text-slate-500">Loading…</p>
              ) : runs.length === 0 ? (
                <p className="text-sm text-slate-500">No runs yet.</p>
              ) : (
                <ul className="space-y-2">
                  {runs.map((r) => (
                    <li key={r.id}>
                      <button
                        onClick={() => void loadDetail(r.id)}
                        className={`w-full text-left px-3 py-2 rounded-lg border text-sm hover:bg-slate-50 ${
                          selected?.id === r.id ? 'border-blue-300 bg-blue-50' : 'border-slate-200'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate font-medium text-slate-800">{r.goal}</span>
                          <span className={`shrink-0 px-2 py-0.5 rounded-full text-xs ${statusColor[r.status] ?? 'bg-slate-100'}`}>
                            {r.status}
                          </span>
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Run detail */}
          <div className="lg:col-span-2 bg-white rounded-xl shadow-sm p-4 border border-slate-200">
            {!selected ? (
              <p className="text-sm text-slate-500">Select a run to inspect its steps and approvals.</p>
            ) : (
              <div>
                <div className="flex items-start justify-between gap-3 mb-4">
                  <div>
                    <h2 className="font-semibold text-slate-900">{selected.goal}</h2>
                    <p className="text-xs text-slate-500 font-mono mt-1">{selected.id}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${statusColor[selected.status] ?? 'bg-slate-100'}`}>
                      {selected.status}
                    </span>
                    {!TERMINAL.has(selected.status) && (
                      <button
                        onClick={() => void api.agent.cancel(selected.id).then(setSelected).then(() => loadRuns())}
                        className="px-3 py-1 border border-slate-200 rounded-lg text-xs hover:bg-slate-50"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
                {selected.error && (
                  <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
                    {selected.error}
                  </div>
                )}
                <ol className="space-y-3">
                  {selected.steps.map((s) => (
                    <li key={s.seq} className="border border-slate-200 rounded-lg p-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-sm font-medium text-slate-800">
                          {s.seq + 1}. {s.tool}
                        </span>
                        <span className={`px-2 py-0.5 rounded-full text-xs ${statusColor[s.status] ?? 'bg-slate-100'}`}>
                          {s.status}
                        </span>
                      </div>
                      {s.error && <p className="text-xs text-red-600 mt-1">{s.error}</p>}
                      {s.output && (
                        <pre className="mt-2 text-xs bg-slate-50 rounded p-2 overflow-auto max-h-40">
                          {JSON.stringify(s.output, null, 2)}
                        </pre>
                      )}
                      {s.status === 'waiting_approval' && (
                        <div className="mt-2 p-2 bg-sky-50 border border-sky-200 rounded-lg">
                          <p className="text-xs text-sky-800 flex items-center gap-1 mb-2">
                            <ShieldAlert className="w-3 h-3" /> Waiting for approval (a colleague must decide — four-eyes)
                          </p>
                          <div className="flex gap-2">
                            <input
                              value={comment}
                              onChange={(e) => setComment(e.target.value)}
                              placeholder="Comment (optional)"
                              className="flex-1 px-2 py-1 border border-slate-200 rounded text-xs"
                            />
                            <button
                              onClick={() => void decide(s.seq, true)}
                              className="flex items-center gap-1 px-3 py-1 bg-emerald-600 text-white rounded text-xs"
                            >
                              <CheckCircle className="w-3 h-3" /> Approve
                            </button>
                            <button
                              onClick={() => void decide(s.seq, false)}
                              className="flex items-center gap-1 px-3 py-1 bg-red-600 text-white rounded text-xs"
                            >
                              <XCircle className="w-3 h-3" /> Reject
                            </button>
                          </div>
                        </div>
                      )}
                      {s.approved_by && (
                        <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                          <Clock className="w-3 h-3" /> Decided by {s.approved_by} · {s.approval_status}
                        </p>
                      )}
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
