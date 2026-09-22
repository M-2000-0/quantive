import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { personalApi, type PersonalScore, type PersonalOpp, type PersonalTask } from '../api';
import { Shield, Lightbulb, TrendingUp, AlertTriangle, ArrowRight, Zap } from 'lucide-react';

export default function PersonalDashboard() {
  const [score, setScore] = useState<PersonalScore | null>(null);
  const [opps, setOpps] = useState<PersonalOpp[]>([]);
  const [tasks, setTasks] = useState<PersonalTask[]>([]);
  const [compliance, setCompliance] = useState<any>(null);
  const [recs, setRecs] = useState<any>(null);
  const [projection, setProjection] = useState<any>(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const [s, o, t] = await Promise.all([
          personalApi.score(), personalApi.opportunities(), personalApi.tasks(),
        ]);
        setScore(s); setOpps(o); setTasks(t.filter((x) => x.status === 'open'));
        // Load new data in parallel
        Promise.all([
          personalApi.complianceStatus().catch(() => null),
          personalApi.recommendations().catch(() => null),
          personalApi.projection().catch(() => null),
        ]).then(([c, r, p]) => {
          setCompliance(c); setRecs(r); setProjection(p);
        });
      } catch (e: any) { setErr(e.message || 'Failed to load'); }
    })();
  }, []);

  if (err) return <div className="qp-warn">{err}</div>;
  if (!score) return <p className="qp-muted">Loading your tax intelligence…</p>;

  const starter = score.tier === 'personal_2k' || score.tier === 'none';
  const oppCap = (score.limits || {}).personal_opportunities;
  const docCap = (score.limits || {}).personal_documents;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Tax Intelligence Dashboard</h1>
        <p className="text-zinc-400 mt-1">{score.message}</p>
        <p className="text-zinc-500 text-sm mt-1">Plan: <strong>{score.tier}</strong>
          {starter && <> · <Link to="/personal/pricing" className="text-blue-400 hover:text-blue-300"> Upgrade →</Link></>}
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Link to="/personal" className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 hover:border-zinc-700 transition-colors">
          <p className="text-zinc-400 text-sm">Intelligence Score</p>
          <p className="text-white text-3xl font-bold">{score.score}</p>
          <p className="text-zinc-500 text-xs">Completeness {score.completeness}%</p>
        </Link>
        <Link to="/personal/compliance" className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 hover:border-zinc-700 transition-colors">
          <div className="flex items-center gap-2 mb-1">
            <Shield className="w-4 h-4 text-blue-400" />
            <p className="text-zinc-400 text-sm">Compliance</p>
          </div>
          <p className={`text-3xl font-bold ${compliance?.score >= 80 ? 'text-emerald-400' : compliance?.score >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
            {compliance?.score ?? '—'}
          </p>
          <p className="text-zinc-500 text-xs">{compliance?.alerts?.length ?? 0} alerts</p>
        </Link>
        <Link to="/personal/recommendations" className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 hover:border-zinc-700 transition-colors">
          <div className="flex items-center gap-2 mb-1">
            <Lightbulb className="w-4 h-4 text-amber-400" />
            <p className="text-zinc-400 text-sm">Recommendations</p>
          </div>
          <p className="text-white text-3xl font-bold">{recs?.total ?? '—'}</p>
          <p className="text-zinc-500 text-xs">Personalized actions</p>
        </Link>
        <Link to="/personal/projection" className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 hover:border-zinc-700 transition-colors">
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-4 h-4 text-purple-400" />
            <p className="text-zinc-400 text-sm">Projected Tax</p>
          </div>
          <p className="text-white text-3xl font-bold">
            {projection ? `$${(projection.total_tax / 100).toLocaleString()}` : '—'}
          </p>
          <p className="text-zinc-500 text-xs">{projection?.bracket || '2026 estimate'}</p>
        </Link>
      </div>

      {/* Compliance Alerts */}
      {compliance?.alerts?.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
            Active Alerts ({compliance.alerts.length})
          </h2>
          <div className="space-y-2">
            {compliance.alerts.slice(0, 3).map((alert: any) => (
              <Link key={alert.id} to="/personal/compliance"
                    className="block bg-zinc-900 rounded-lg border border-zinc-800 p-3 hover:border-zinc-700 transition-colors">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${
                    alert.severity === 'critical' ? 'bg-red-500' :
                    alert.severity === 'warning' ? 'bg-amber-500' : 'bg-blue-500'
                  }`} />
                  <div className="flex-1">
                    <p className="text-white text-sm font-medium">{alert.title}</p>
                    <p className="text-zinc-400 text-xs">{alert.description}</p>
                  </div>
                  <ArrowRight className="w-4 h-4 text-zinc-500" />
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Top Recommendations */}
      {recs?.recommendations?.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Lightbulb className="w-5 h-5 text-amber-400" />
              Top Recommendations
            </h2>
            <Link to="/personal/recommendations" className="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-1">
              View all <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="space-y-2">
            {recs.recommendations.slice(0, 3).map((rec: any) => (
              <Link key={rec.id} to="/personal/recommendations"
                    className="block bg-zinc-900 rounded-lg border border-zinc-800 p-4 hover:border-zinc-700 transition-colors">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        rec.priority === 'high' ? 'bg-red-900/50 text-red-300 border border-red-800' :
                        'bg-amber-900/50 text-amber-300 border border-amber-800'
                      }`}>{rec.priority}</span>
                      <span className="text-zinc-500 text-xs">{rec.type}</span>
                    </div>
                    <p className="text-white font-medium">{rec.title}</p>
                    <p className="text-zinc-400 text-sm mt-1 line-clamp-1">{rec.why}</p>
                  </div>
                  {rec.estimated_savings_max > 0 && (
                    <p className="text-emerald-400 font-semibold text-sm shrink-0 ml-4">
                      +${(rec.estimated_savings_max / 100).toLocaleString()}
                    </p>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link to="/personal/connections" className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 hover:border-zinc-700 transition-colors flex items-center gap-3">
          <Zap className="w-8 h-8 text-blue-400" />
          <div>
            <p className="text-white font-medium">Connect Bank Account</p>
            <p className="text-zinc-400 text-sm">Enable real-time transaction tracking</p>
          </div>
        </Link>
        <Link to="/personal/projection" className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 hover:border-zinc-700 transition-colors flex items-center gap-3">
          <TrendingUp className="w-8 h-8 text-purple-400" />
          <div>
            <p className="text-white font-medium">View Tax Projection</p>
            <p className="text-zinc-400 text-sm">See your 2026 estimate and what-if scenarios</p>
          </div>
        </Link>
      </div>

      {/* Opportunities */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-white">Detected Opportunities</h2>
          <Link to="/personal/opportunities" className="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-1">
            View all <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
        <div className="space-y-2">
          {opps.slice(0, 4).map((o) => (
            <div key={o.id} className="bg-zinc-900 rounded-lg border border-zinc-800 p-3">
              <div className="flex items-center gap-2 mb-1">
                <span className={`px-2 py-0.5 rounded text-xs ${
                  o.relevance === 'high' ? 'bg-red-900/50 text-red-300' :
                  o.relevance === 'medium' ? 'bg-amber-900/50 text-amber-300' :
                  'bg-zinc-800 text-zinc-400'
                }`}>{o.relevance}</span>
                <span className="text-zinc-500 text-xs capitalize">{o.category}</span>
              </div>
              <p className="text-white font-medium">{o.title}</p>
              <p className="text-zinc-400 text-sm mt-1">{o.why}</p>
            </div>
          ))}
          {opps.length === 0 && (
            <p className="text-zinc-500 text-sm">Complete onboarding to detect opportunities. <Link to="/personal/onboarding" className="text-blue-400">Start →</Link></p>
          )}
        </div>
      </div>

      {/* Tasks */}
      {tasks.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-white mb-3">Open Tasks</h2>
          <div className="space-y-2">
            {tasks.slice(0, 3).map((t) => (
              <div key={t.id} className="bg-zinc-900 rounded-lg border border-zinc-800 p-3">
                <p className="text-white font-medium">{t.title}</p>
                <p className="text-zinc-400 text-sm mt-1">{t.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {starter && (
        <div className="bg-zinc-900 rounded-xl border border-amber-800 p-4">
          <p className="text-amber-200 text-sm">
            <strong>Starter plan:</strong> Up to {oppCap ?? 3} opportunities, {docCap ?? 10} documents.
            <Link to="/personal/pricing" className="text-amber-400 hover:text-amber-300 ml-2">Compare plans →</Link>
          </p>
        </div>
      )}
    </div>
  );
}
