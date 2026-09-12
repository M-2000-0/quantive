import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { BarChart3, Globe, TrendingUp, Users, Search, Filter, ChevronDown } from 'lucide-react';
import { api } from '../api';

interface CountryRanking {
  rank: number;
  country_code: string;
  country_name: string;
  region: string;
  income_group: string;
  overall_score: number;
  tier: string;
  category_scores: {
    disclosure: number;
    data_access: number;
    institutional: number;
    reporting_freq: number;
    audit_trail: number;
    digital_infra: number;
    compliance: number;
    stakeholder: number;
  };
}

interface GlobalStats {
  total_countries: number;
  avg_score: number;
  top_performers: Array<{ code: string; name: string; score: number }>;
  bottom_performers: Array<{ code: string; name: string; score: number }>;
}

interface Methodology {
  version: string;
  title: string;
  description: string;
  category_weights: Record<string, number>;
  categories: Array<{
    name: string;
    label: string;
    weight: number;
    description: string;
  }>;
}

const TIER_COLORS: Record<string, string> = {
  leader: 'bg-emerald-100 text-emerald-800',
  advanced: 'bg-blue-100 text-blue-800',
  developing: 'bg-amber-100 text-amber-800',
  emerging: 'bg-orange-100 text-orange-800',
  laggard: 'bg-red-100 text-red-800',
};

const TIER_LABELS: Record<string, string> = {
  leader: 'Leader (80-100)',
  advanced: 'Advanced (60-79)',
  developing: 'Developing (40-59)',
  emerging: 'Emerging (20-39)',
  laggard: 'Laggard (0-19)',
};

const REGIONS = [
  'Africa', 'Asia', 'Europe', 'Latin America', 'Middle East', 'North America', 'Oceania'
];

const INCOME_GROUPS = [
  'Low income', 'Lower-middle', 'Upper-middle', 'High income'
];

function formatScore(score: number): string {
  return score.toFixed(1);
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'text-emerald-600';
  if (score >= 60) return 'text-blue-600';
  if (score >= 40) return 'text-amber-600';
  if (score >= 20) return 'text-orange-600';
  return 'text-red-600';
}

function getScoreBg(score: number): string {
  if (score >= 80) return 'bg-emerald-500';
  if (score >= 60) return 'bg-blue-500';
  if (score >= 40) return 'bg-amber-500';
  if (score >= 20) return 'bg-orange-500';
  return 'bg-red-500';
}

export default function TransparencyIndexPage() {
  const [rankings, setRankings] = useState<CountryRanking[]>([]);
  const [stats, setStats] = useState<GlobalStats | null>(null);
  const [methodology, setMethodology] = useState<Methodology | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRegion, setSelectedRegion] = useState<string>('');
  const [selectedTier, setSelectedTier] = useState<string>('');
  const [selectedCountry, setSelectedCountry] = useState<CountryRanking | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [countriesData, statsData] = await Promise.all([
        api.transparencyIndex.allCountries().catch(() => []),
        api.transparencyIndex.globalStats().catch(() => null),
      ]);
      setRankings((countriesData || []).map((c, idx) => ({
        rank: c.rank || idx + 1,
        country_code: c.code,
        country_name: c.name,
        region: '',
        income_group: '',
        overall_score: c.overall_score,
        tier: c.overall_score >= 80 ? 'leader' : c.overall_score >= 60 ? 'advanced' : c.overall_score >= 40 ? 'developing' : c.overall_score >= 20 ? 'emerging' : 'laggard',
        category_scores: {
          disclosure: 0,
          data_access: 0,
          institutional: 0,
          reporting_freq: 0,
          audit_trail: 0,
          digital_infra: 0,
          compliance: 0,
          stakeholder: 0,
        },
      })));
      setStats(statsData);
      setMethodology(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const filteredRankings = useMemo(() => {
    let filtered = rankings;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (r) =>
          r.country_name.toLowerCase().includes(q) ||
          r.country_code.toLowerCase().includes(q)
      );
    }
    if (selectedRegion) {
      filtered = filtered.filter((r) => r.region === selectedRegion);
    }
    if (selectedTier) {
      filtered = filtered.filter((r) => r.tier === selectedTier);
    }
    return filtered;
  }, [rankings, searchQuery, selectedRegion, selectedTier]);

  const categoryLabels: Record<string, string> = {
    disclosure: 'Disclosure',
    data_access: 'Data Access',
    institutional: 'Institutional',
    reporting_freq: 'Reporting',
    audit_trail: 'Audit',
    digital_infra: 'Digital',
    compliance: 'Compliance',
    stakeholder: 'Stakeholder',
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-slate-200 rounded w-1/3"></div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-24 bg-slate-200 rounded-lg"></div>
              ))}
            </div>
            <div className="h-96 bg-slate-200 rounded-lg"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-red-800 font-semibold">Error Loading Data</h2>
            <p className="text-red-600 mt-2">{error}</p>
            <button
              onClick={loadData}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
            <Globe className="w-8 h-8 text-blue-600" />
            Sovereign Debt Transparency Index
          </h1>
          <p className="text-slate-600 mt-2">
            Ranking countries on the transparency and sophistication of their debt management practices.
          </p>
        </div>

        {/* Global Stats */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
              <div className="text-sm text-slate-500">Countries Ranked</div>
              <div className="text-2xl font-bold text-slate-900">{stats.total_countries}</div>
            </div>
            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
              <div className="text-sm text-slate-500">Global Average</div>
              <div className="text-2xl font-bold text-blue-600">{formatScore(stats.avg_score)}</div>
            </div>
            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
              <div className="text-sm text-slate-500">Highest Score</div>
              <div className="text-2xl font-bold text-emerald-600">{stats.top_performers?.[0]?.score ? formatScore(stats.top_performers[0].score) : 'N/A'}</div>
            </div>
            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
              <div className="text-sm text-slate-500">Lowest Score</div>
              <div className="text-2xl font-bold text-red-600">{stats.bottom_performers?.[0]?.score ? formatScore(stats.bottom_performers[0].score) : 'N/A'}</div>
            </div>
            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
              <div className="text-sm text-slate-500">Top Performers</div>
              <div className="text-2xl font-bold text-emerald-600">
                {stats.top_performers?.length || 0}
              </div>
            </div>
          </div>
        )}

        {/* Tier Distribution */}
        {stats && (
          <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200 mb-8">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Top Performers</h2>
            <div className="flex flex-wrap gap-4">
              {stats.top_performers?.slice(0, 5).map((country) => (
                <div key={country.code} className="flex items-center gap-2">
                  <span className="px-3 py-1 rounded-full text-sm font-medium bg-emerald-100 text-emerald-800">
                    {country.name}: {formatScore(country.score)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200 mb-8">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search countries..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>
            <select
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
              className="px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Regions</option>
              {REGIONS.map((region) => (
                <option key={region} value={region}>
                  {region}
                </option>
              ))}
            </select>
            <select
              value={selectedTier}
              onChange={(e) => setSelectedTier(e.target.value)}
              className="px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Tiers</option>
              {Object.entries(TIER_LABELS).map(([tier, label]) => (
                <option key={tier} value={tier}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Rankings Table */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden mb-8">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Rank
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Country
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Region
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Score
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Tier
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Category Scores
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredRankings.map((country) => (
                  <tr key={country.country_code} className="hover:bg-slate-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="font-bold text-slate-900">#{country.rank}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <span className="text-2xl mr-3">
                          {country.country_code === 'US' ? '🇺🇸' :
                           country.country_code === 'GB' ? '🇬🇧' :
                           country.country_code === 'DE' ? '🇩🇪' :
                           country.country_code === 'JP' ? '🇯🇵' :
                           country.country_code === 'AU' ? '🇦🇺' :
                           '🏳️'}
                        </span>
                        <div>
                          <div className="font-medium text-slate-900">{country.country_name}</div>
                          <div className="text-sm text-slate-500">{country.income_group}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                      {country.region}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${getScoreBg(country.overall_score)}`}
                            style={{ width: `${country.overall_score}%` }}
                          ></div>
                        </div>
                        <span className={`font-bold ${getScoreColor(country.overall_score)}`}>
                          {formatScore(country.overall_score)}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${TIER_COLORS[country.tier]}`}>
                        {country.tier}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex gap-1 flex-wrap">
                        {Object.entries(country.category_scores).map(([key, score]) => (
                          <span
                            key={key}
                            className="px-2 py-0.5 text-xs rounded bg-slate-100 text-slate-600"
                            title={categoryLabels[key]}
                          >
                            {categoryLabels[key]}: {formatScore(score as number)}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <button
                        onClick={() => setSelectedCountry(country)}
                        className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Methodology */}
        {methodology && (
          <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Methodology</h2>
            <p className="text-slate-600 mb-4">{methodology.description}</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {methodology.categories.map((cat) => (
                <div key={cat.name} className="flex items-center gap-3">
                  <div className="w-24 text-sm text-slate-500">{cat.label}</div>
                  <div className="flex-1 bg-slate-200 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full"
                      style={{ width: `${cat.weight * 100}%` }}
                    ></div>
                  </div>
                  <div className="text-sm font-medium text-slate-700">{(cat.weight * 100).toFixed(0)}%</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Country Detail Modal */}
        {selectedCountry && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h2 className="text-xl font-bold text-slate-900">{selectedCountry.country_name}</h2>
                    <p className="text-slate-500">{selectedCountry.region} • {selectedCountry.income_group}</p>
                  </div>
                  <button
                    onClick={() => setSelectedCountry(null)}
                    className="text-slate-400 hover:text-slate-600"
                  >
                    ✕
                  </button>
                </div>

                <div className="mb-6">
                  <div className="flex items-center gap-4">
                    <div className={`text-4xl font-bold ${getScoreColor(selectedCountry.overall_score)}`}>
                      {formatScore(selectedCountry.overall_score)}
                    </div>
                    <div>
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${TIER_COLORS[selectedCountry.tier]}`}>
                        {TIER_LABELS[selectedCountry.tier]}
                      </span>
                      <div className="text-sm text-slate-500 mt-1">Rank #{selectedCountry.rank}</div>
                    </div>
                  </div>
                </div>

                <h3 className="font-semibold text-slate-900 mb-3">Category Scores</h3>
                <div className="space-y-3 mb-6">
                  {Object.entries(selectedCountry.category_scores).map(([key, score]) => (
                    <div key={key} className="flex items-center gap-3">
                      <div className="w-28 text-sm text-slate-600">{categoryLabels[key]}</div>
                      <div className="flex-1 bg-slate-200 rounded-full h-3">
                        <div
                          className={`h-3 rounded-full ${getScoreBg(score as number)}`}
                          style={{ width: `${score}%` }}
                        ></div>
                      </div>
                      <div className="w-12 text-right text-sm font-medium">{formatScore(score as number)}</div>
                    </div>
                  ))}
                </div>

                <div className="flex gap-3">
                  <Link
                    to={`/transparency-index/${selectedCountry.country_code}`}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    Full Report
                  </Link>
                  <button
                    onClick={() => setSelectedCountry(null)}
                    className="px-4 py-2 bg-slate-200 text-slate-700 rounded-lg hover:bg-slate-300"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
