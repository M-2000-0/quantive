interface QualityScore {
  category: string;
  score: number; // 0-100
  details: string;
}

interface DataQualityIndicatorProps {
  scores: QualityScore[];
  overallScore?: number;
  lastRefreshed?: string;
  dataFreshness?: 'live' | 'delayed' | 'stale' | 'unknown';
}

export default function DataQualityIndicator({
  scores, overallScore, lastRefreshed, dataFreshness = 'live' }: DataQualityIndicatorProps) {
  const computed = overallScore ?? scores.reduce((sum, s) => sum + s.score, 0) / scores.length;

  const freshnessConfig = {
    live: { label: 'Live', color: 'bg-green-400', textColor: 'text-green-400' },
    delayed: { label: 'Delayed', color: 'bg-yellow-400', textColor: 'text-yellow-400' },
    stale: { label: 'Stale', color: 'bg-red-400', textColor: 'text-red-400' },
    unknown: { label: 'Unknown', color: 'bg-gray-400', textColor: 'text-gray-400' } };

  const freshness = freshnessConfig[dataFreshness];

  const getScoreColor = (score: number) => {
    if (score >= 90) return '#10b981';
    if (score >= 70) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div className="glass-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white/80">Data Quality</h3>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${freshness.color} animate-pulse`} />
          <span className={`text-[10px] font-medium ${freshness.textColor}`}>{freshness.label}</span>
          {lastRefreshed && <span className="text-[10px] text-white/30">• {lastRefreshed}</span>}
        </div>
      </div>

      {/* Overall score */}
      <div className="flex items-center gap-4 mb-4">
        <svg width="60" height="60" viewBox="0 0 60 60">
          <circle cx="30" cy="30" r="25" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="5" />
          <circle
            cx="30" cy="30" r="25" fill="none"
            stroke={getScoreColor(computed)}
            strokeWidth="5"
            strokeDasharray={`${(computed / 100) * 157} 157`}
            strokeLinecap="round"
            transform="rotate(-90 30 30)"
          />
          <text x="30" y="34" textAnchor="middle" fill="white" fontSize="14" fontWeight="700">
            {computed.toFixed(0)}
          </text>
        </svg>
        <div>
          <p className="text-sm font-medium text-white">Overall Quality Score</p>
          <p className="text-xs text-white/40">
            {computed >= 90 ? 'Excellent' : computed >= 70 ? 'Good' : 'Needs Attention'}
          </p>
        </div>
      </div>

      {/* Category scores */}
      <div className="space-y-2">
        {scores.map((s) => (
          <div key={s.category}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-white/60">{s.category}</span>
              <span className="text-xs font-medium" style={{ color: getScoreColor(s.score) }}>{s.score}%</span>
            </div>
            <div className="w-full bg-white/5 rounded-full h-1.5">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${s.score}%`, backgroundColor: getScoreColor(s.score) }}
              />
            </div>
            <p className="text-[10px] text-white/30 mt-0.5">{s.details}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
