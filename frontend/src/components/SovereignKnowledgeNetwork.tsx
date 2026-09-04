import { useState, useEffect, useCallback } from 'react';
import Card, { CardHeader } from './ui/Card';
import Badge from './ui/Badge';
import Button from './ui/Button';

interface Pattern {
  id: string;
  name: string;
  description: string;
  confidence: number;
  sampleSize: number;
  countries: string[];
  lastSeen: string;
  category: 'optimization' | 'risk' | 'market' | 'institutional';
}

const MOCK_PATTERNS: Pattern[] = [
  {
    id: 'p1',
    name: 'Duration Extension Best in Low-Rate Environments',
    description: 'Countries that extended average maturity by 2+ years during rate troughs reduced refinancing risk by 34% over the subsequent 5 years. Pattern observed in 12 sovereign debt portfolios.',
    confidence: 87,
    sampleSize: 47,
    countries: ['MX', 'CO', 'ID', 'ZA', 'BR'],
    lastSeen: '2026-08-15',
    category: 'optimization' },
  {
    id: 'p2',
    name: 'Currency Diversification Reduces Tail Risk',
    description: 'Portfolios with 3+ currency exposures showed 23% lower maximum drawdown during FX crises compared to single-currency portfolios. Consistent across emerging and developed markets.',
    confidence: 91,
    sampleSize: 63,
    countries: ['CL', 'PE', 'TH', 'MY', 'PL'],
    lastSeen: '2026-08-20',
    category: 'risk' },
  {
    id: 'p3',
    name: 'Pre-Election Issuance Timing Matters',
    description: 'Governments that completed major issuances 6+ months before elections achieved 12bps lower average coupon than those issuing within 3 months of elections.',
    confidence: 78,
    sampleSize: 38,
    countries: ['AR', 'TR', 'NG', 'KE', 'PH'],
    lastSeen: '2026-08-10',
    category: 'institutional' },
  {
    id: 'p4',
    name: 'Green Bond Premium Convergence',
    description: 'The "greenium" (yield advantage of green bonds) has compressed from 8bps to 2bps over 3 years. Countries issuing green bonds at par with conventional bonds now capture ESG investment flows without yield sacrifice.',
    confidence: 82,
    sampleSize: 29,
    countries: ['FR', 'DE', 'UK', 'JP', 'KR'],
    lastSeen: '2026-08-22',
    category: 'market' },
  {
    id: 'p5',
    name: 'Floating Rate Exposure Amplifies Rate Shock',
    description: 'Portfolios with >30% floating-rate instruments experienced 2.3x greater interest expense increase during rate hikes compared to fixed-rate dominated portfolios.',
    confidence: 94,
    sampleSize: 71,
    countries: ['US', 'AU', 'NZ', 'CA', 'SE'],
    lastSeen: '2026-08-18',
    category: 'risk' },
  {
    id: 'p6',
    name: 'Bilateral Loan Renegotiation Windows',
    description: 'Countries that renegotiated bilateral loans during IMF program reviews achieved 15-25bps better terms than those negotiating independently.',
    confidence: 73,
    sampleSize: 22,
    countries: ['GH', 'ZM', 'ET', 'BD', 'PK'],
    lastSeen: '2026-07-30',
    category: 'institutional' },
];

const CATEGORY_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  optimization: { label: 'Optimization', color: 'text-blue-700 bg-blue-500/12 border-blue-500/20', icon: 'Zap' },
  risk: { label: 'Risk', color: 'text-red-700 bg-red-500/12 border-red-500/20', icon: 'Shield' },
  market: { label: 'Market', color: 'text-emerald-700 bg-emerald-500/12 border-emerald-500/20', icon: 'TrendingUp' },
  institutional: { label: 'Institutional', color: 'text-violet-700 bg-violet-500/12 border-violet-500/20', icon: 'Building2' } };

export default function SovereignKnowledgeNetwork() {
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');
  const [selectedPattern, setSelectedPattern] = useState<Pattern | null>(null);

  const fetchPatterns = useCallback(async () => {
    setLoading(true);
    // In production: api.knowledge.patterns()
    await new Promise((r) => setTimeout(r, 600));
    setPatterns(MOCK_PATTERNS);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchPatterns();
  }, [fetchPatterns]);

  const filtered = filter === 'all' ? patterns : patterns.filter((p) => p.category === filter);
  const totalCountries = new Set(patterns.flatMap((p) => p.countries)).size;
  const avgConfidence = patterns.length > 0 ? Math.round(patterns.reduce((s, p) => s + p.confidence, 0) / patterns.length) : 0;

  return (
    <div className="space-y-6">
      {/* Header stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <div className="p-4 text-center">
            <p className="text-2xl font-bold text-slate-900">{patterns.length}</p>
            <p className="text-xs text-slate-500 mt-1">Patterns Learned</p>
          </div>
        </Card>
        <Card>
          <div className="p-4 text-center">
            <p className="text-2xl font-bold text-blue-600">{totalCountries}</p>
            <p className="text-xs text-slate-500 mt-1">Countries Observed</p>
          </div>
        </Card>
        <Card>
          <div className="p-4 text-center">
            <p className="text-2xl font-bold text-emerald-600">{avgConfidence}%</p>
            <p className="text-xs text-slate-500 mt-1">Avg Confidence</p>
          </div>
        </Card>
        <Card>
          <div className="p-4 text-center">
            <p className="text-2xl font-bold text-violet-600">{patterns.reduce((s, p) => s + p.sampleSize, 0)}</p>
            <p className="text-xs text-slate-500 mt-1">Total Observations</p>
          </div>
        </Card>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-2">
        {['all', 'optimization', 'risk', 'market', 'institutional'].map((cat) => (
          <button
            key={cat}
            onClick={() => setFilter(cat)}
            className={`px-3 py-1.5 text-xs font-medium rounded-full border backdrop-blur transition-all ${
              filter === cat
                ? 'bg-slate-900 text-white border-slate-900'
                : 'bg-white/60 text-slate-600 border-white/60 hover:bg-white/80'
            }`}
          >
            {cat === 'all' ? 'All Patterns' : CATEGORY_CONFIG[cat]?.icon + ' ' + CATEGORY_CONFIG[cat]?.label}
          </button>
        ))}
      </div>

      {/* Patterns list */}
      <div className="space-y-4">
        {loading ? (
          <Card>
            <div className="p-12 text-center text-slate-400">Loading patterns from the knowledge network...</div>
          </Card>
        ) : filtered.length === 0 ? (
          <Card>
            <div className="p-12 text-center text-slate-400">No patterns found for this category.</div>
          </Card>
        ) : (
          filtered.map((pattern) => {
            const cat = CATEGORY_CONFIG[pattern.category];
            return (
              <Card key={pattern.id} padding={false}>
                <div
                  className="px-6 py-5 cursor-pointer hover:bg-white/30 transition-colors"
                  onClick={() => setSelectedPattern(selectedPattern?.id === pattern.id ? null : pattern)}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <span className="text-lg">{cat?.icon}</span>
                      <div>
                        <h3 className="text-[15px] font-bold text-slate-900">{pattern.name}</h3>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {pattern.sampleSize} observations · {pattern.countries.length} countries
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={pattern.confidence >= 85 ? 'success' : pattern.confidence >= 70 ? 'warning' : 'danger'}>
                        {pattern.confidence}% confidence
                      </Badge>
                      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold border ${cat?.color}`}>
                        {cat?.label}
                      </span>
                    </div>
                  </div>

                  {selectedPattern?.id === pattern.id && (
                    <div className="mt-4 pt-4 border-t border-white/40 space-y-3">
                      <p className="text-sm text-slate-700 leading-relaxed">{pattern.description}</p>
                      <div className="flex flex-wrap gap-2">
                        {pattern.countries.map((c) => (
                          <span key={c} className="px-2 py-0.5 text-[10px] font-bold bg-slate-100 text-slate-600 rounded-full">
                            {c}
                          </span>
                        ))}
                      </div>
                      <p className="text-[11px] text-slate-400">Last observed: {new Date(pattern.lastSeen).toLocaleDateString()}</p>
                    </div>
                  )}
                </div>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}
