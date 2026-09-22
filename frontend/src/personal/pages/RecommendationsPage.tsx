import { useEffect, useState } from 'react';
import { personalApi } from '../api';
import { Lightbulb, ChevronDown, ChevronUp, CheckCircle, XCircle, ArrowRight, DollarSign, Clock, AlertCircle } from 'lucide-react';

export default function RecommendationsPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    personalApi.recommendations().then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const handleStatus = async (id: string, status: string) => {
    await personalApi.updateRecommendation(id, status);
    setData((prev: any) => ({
      ...prev,
      recommendations: prev.recommendations.map((r: any) =>
        r.id === id ? { ...r, status } : r
      ),
    }));
  };

  if (loading) return <div className="p-8 text-zinc-400">Loading recommendations...</div>;
  if (!data?.recommendations?.length) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Recommendations</h1>
          <p className="text-zinc-400 mt-1">Personalized tax-saving actions</p>
        </div>
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-12 text-center">
          <Lightbulb className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
          <p className="text-zinc-400">No recommendations yet. Complete your profile and connect accounts to get started.</p>
        </div>
      </div>
    );
  }

  const priorityColor = (p: string) => p === 'high' ? 'text-red-400 bg-red-950/50 border-red-800' :
    p === 'medium' ? 'text-amber-400 bg-amber-950/50 border-amber-800' : 'text-zinc-400 bg-zinc-800 border-zinc-700';
  const typeIcon = (t: string) => {
    switch (t) {
      case 'compliance': return <AlertCircle className="w-4 h-4" />;
      case 'immediate': return <Clock className="w-4 h-4" />;
      case 'behavioral': return <ArrowRight className="w-4 h-4" />;
      case 'year_end': return <Clock className="w-4 h-4" />;
      case 'strategic': return <Lightbulb className="w-4 h-4" />;
      default: return <Lightbulb className="w-4 h-4" />;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Recommendations</h1>
        <p className="text-zinc-400 mt-1">{data.total} personalized tax-saving actions</p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'High Priority', count: data.recommendations.filter((r: any) => r.priority === 'high').length, color: 'text-red-400' },
          { label: 'Medium Priority', count: data.recommendations.filter((r: any) => r.priority === 'medium').length, color: 'text-amber-400' },
          { label: 'Potential Savings', count: data.recommendations.reduce((s: number, r: any) => s + (r.estimated_savings_max || 0), 0), color: 'text-emerald-400', isDollar: true },
        ].map((s, i) => (
          <div key={i} className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
            <p className="text-zinc-400 text-sm">{s.label}</p>
            <p className={`text-2xl font-bold ${s.color}`}>
              {s.isDollar ? `$${(s.count / 100).toLocaleString()}` : s.count}
            </p>
          </div>
        ))}
      </div>

      {/* Recommendation List */}
      <div className="space-y-3">
        {data.recommendations.map((rec: any) => (
          <div key={rec.id}
               className={`bg-zinc-900 rounded-xl border border-zinc-800 overflow-hidden transition-all ${
                 rec.status === 'accepted' ? 'border-emerald-800' :
                 rec.status === 'dismissed' ? 'opacity-50' : ''
               }`}>
            {/* Header */}
            <div className="p-4 cursor-pointer hover:bg-zinc-800/50 transition-colors"
                 onClick={() => setExpandedId(expandedId === rec.id ? null : rec.id)}>
              <div className="flex items-start gap-3">
                <div className="mt-0.5">{typeIcon(rec.type)}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-medium text-white truncate">{rec.title}</h3>
                    <span className={`px-2 py-0.5 rounded text-xs border ${priorityColor(rec.priority)}`}>
                      {rec.priority}
                    </span>
                  </div>
                  <p className="text-zinc-400 text-sm line-clamp-2">{rec.why}</p>
                </div>
                <div className="text-right shrink-0">
                  {rec.estimated_savings_max > 0 && (
                    <p className="text-emerald-400 font-semibold text-sm">
                      ${(rec.estimated_savings_min / 100).toLocaleString()} – ${(rec.estimated_savings_max / 100).toLocaleString()}
                    </p>
                  )}
                  <p className="text-zinc-500 text-xs mt-1">{rec.confidence} confidence</p>
                </div>
                {expandedId === rec.id ? <ChevronUp className="w-4 h-4 text-zinc-500" /> :
                 <ChevronDown className="w-4 h-4 text-zinc-500" />}
              </div>
            </div>

            {/* Expanded Details */}
            {expandedId === rec.id && (
              <div className="border-t border-zinc-800 p-4 space-y-4">
                {rec.irc_section && (
                  <div className="bg-zinc-800 rounded-lg p-3">
                    <p className="text-zinc-400 text-xs uppercase tracking-wide">Legal Basis</p>
                    <p className="text-white text-sm font-mono">{rec.irc_section}</p>
                  </div>
                )}

                <div>
                  <p className="text-zinc-400 text-xs uppercase tracking-wide mb-2">Why This Matters</p>
                  <p className="text-zinc-300 text-sm">{rec.why}</p>
                </div>

                {rec.action_steps?.length > 0 && (
                  <div>
                    <p className="text-zinc-400 text-xs uppercase tracking-wide mb-2">Action Steps</p>
                    <ol className="space-y-1">
                      {rec.action_steps.map((step: string, i: number) => (
                        <li key={i} className="text-zinc-300 text-sm flex items-start gap-2">
                          <span className="text-zinc-500 shrink-0">{i + 1}.</span>
                          {step}
                        </li>
                      ))}
                    </ol>
                  </div>
                )}

                {rec.risks?.length > 0 && (
                  <div>
                    <p className="text-zinc-400 text-xs uppercase tracking-wide mb-2">Risks to Consider</p>
                    <ul className="space-y-1">
                      {rec.risks.map((risk: string, i: number) => (
                        <li key={i} className="text-amber-400/80 text-sm flex items-start gap-2">
                          <AlertCircle className="w-3 h-3 mt-0.5 shrink-0" />
                          {risk}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {rec.deadline && (
                  <div className="flex items-center gap-2 text-amber-400 text-sm">
                    <Clock className="w-4 h-4" />
                    Deadline: {rec.deadline === 'quarterly' ? 'Quarterly payment deadline' : rec.deadline}
                  </div>
                )}

                {/* Actions */}
                <div className="flex items-center gap-2 pt-2">
                  {rec.status === 'new' && (
                    <>
                      <button onClick={() => handleStatus(rec.id, 'accepted')}
                              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium flex items-center gap-2">
                        <CheckCircle className="w-4 h-4" /> Accept
                      </button>
                      <button onClick={() => handleStatus(rec.id, 'dismissed')}
                              className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg text-sm flex items-center gap-2">
                        <XCircle className="w-4 h-4" /> Dismiss
                      </button>
                    </>
                  )}
                  {rec.status === 'accepted' && (
                    <button onClick={() => handleStatus(rec.id, 'implemented')}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium">
                      Mark Implemented
                    </button>
                  )}
                  {rec.status === 'implemented' && (
                    <span className="text-emerald-400 text-sm flex items-center gap-1">
                      <CheckCircle className="w-4 h-4" /> Implemented
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
