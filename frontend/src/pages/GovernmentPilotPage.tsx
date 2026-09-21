import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Users, Plus, Calendar, DollarSign, TrendingUp, ArrowRight,
  Clock, CheckCircle, AlertTriangle, Search
} from 'lucide-react';
import { api } from '../api';
import type { PilotProgram } from '../types';

interface PilotSummary {
  total_pilots: number;
  active_pilots: number;
  completed_pilots: number;
  converted_pilots: number;
  conversion_rate: number;
  total_debt_managed: number;
  total_conversion_value: number;
}

export default function GovernmentPilotPage() {
  const [pilots, setPilots] = useState<PilotProgram[]>([]);
  const [summary, setSummary] = useState<PilotSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

  const loadPilots = useCallback(async () => {
    setLoading(true);
    try {
      const [dashData, pilotList] = await Promise.all([
        api.pilotProgram.dashboard().catch(() => null),
        api.pilotProgram.list().catch(() => ({ pilots: [] })),
      ]);

      if (dashData?.summary) setSummary(dashData.summary);
      if (pilotList?.pilots) setPilots(pilotList.pilots);
    } catch (e) {
      console.error('Failed to load pilots:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadPilots();
  }, [loadPilots]);

  const filteredPilots = pilots.filter(p => {
    if (filter !== 'all' && p.status !== filter) return false;
    if (search && !p.country_name.toLowerCase().includes(search.toLowerCase()) && !p.government_entity.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const statusColors: Record<string, string> = {
    proposed: 'bg-slate-100 text-slate-700',
    approved: 'bg-blue-100 text-blue-700',
    active: 'bg-emerald-100 text-emerald-700',
    completed: 'bg-purple-100 text-purple-700',
    converted: 'bg-amber-100 text-amber-700',
    failed: 'bg-red-100 text-red-700',
  };

  const formatCurrency = (amount: number) => {
    if (amount >= 1e9) return `$${(amount / 1e9).toFixed(1)}B`;
    if (amount >= 1e6) return `$${(amount / 1e6).toFixed(1)}M`;
    return `$${(amount / 1e3).toFixed(0)}K`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-slate-200 rounded w-1/3"></div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-32 bg-slate-200 rounded-lg"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
              <Users className="w-8 h-8 text-blue-600" />
              Government Pilot Programs
            </h1>
            <p className="text-slate-600 mt-2">
              Track and manage government debt optimization pilot programs.
            </p>
          </div>
          <Link
            to="/pilots/new"
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" />
            New Pilot
          </Link>
        </div>

        {/* Summary Cards */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Users className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <div className="text-sm text-slate-500">Active Pilots</div>
                  <div className="text-2xl font-bold text-slate-900">{summary.active_pilots}</div>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-emerald-100 rounded-lg flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-emerald-600" />
                </div>
                <div>
                  <div className="text-sm text-slate-500">Total Programs</div>
                  <div className="text-2xl font-bold text-slate-900">{summary.total_pilots}</div>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-amber-100 rounded-lg flex items-center justify-center">
                  <DollarSign className="w-6 h-6 text-amber-600" />
                </div>
                <div>
                  <div className="text-sm text-slate-500">Completed</div>
                  <div className="text-2xl font-bold text-slate-900">{summary.completed_pilots}</div>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                  <Calendar className="w-6 h-6 text-purple-600" />
                </div>
                <div>
                  <div className="text-sm text-slate-500">Conversion Rate</div>
                  <div className="text-2xl font-bold text-slate-900">{summary.conversion_rate}%</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-xl shadow-sm p-4 border border-slate-200 mb-6">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-slate-100 rounded-lg p-1">
              {['all', 'proposed', 'active', 'completed', 'converted'].map(f => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-3 py-1 rounded-md text-sm font-medium capitalize ${
                    filter === f ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
            <div className="flex-1 flex items-center gap-2 bg-slate-100 rounded-lg px-3 py-2">
              <Search className="w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search by country..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="bg-transparent border-none outline-none text-sm w-full"
              />
            </div>
          </div>
        </div>

        {/* Pilot List */}
        {filteredPilots.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm p-12 border border-slate-200 text-center">
            <Users className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-900 mb-2">No pilot programs found</h3>
            <p className="text-slate-500 mb-4">
              {search ? 'No pilots match your search criteria.' : 'Start your first government pilot program.'}
            </p>
            <Link
              to="/pilots/new"
              className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" />
              Create Pilot Program
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredPilots.map(pilot => (
              <div
                key={pilot.id}
                className="bg-white rounded-xl shadow-sm p-6 border border-slate-200 hover:shadow-md transition-shadow"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center text-xl">
                      🏛️
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-900">{pilot.government_entity}</h3>
                      <div className="text-sm text-slate-500">
                        {pilot.country_name} · {pilot.entity_type}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="text-sm text-slate-500">Start Date</div>
                      <div className="font-bold text-emerald-600">
                        {pilot.start_date}
                      </div>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusColors[pilot.status] || 'bg-slate-100 text-slate-700'}`}>
                      {pilot.status}
                    </span>
                    <ArrowRight className="w-5 h-5 text-slate-400" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
