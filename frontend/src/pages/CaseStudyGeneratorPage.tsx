import { useCallback, useEffect, useState } from 'react';
import { FileText, Download, Edit3, CheckCircle, Clock, Users, TrendingUp } from 'lucide-react';
import { api } from '../api';

interface Pilot {
  id: string;
  country_code: string;
  country_name: string;
  government_entity: string;
  entity_type: string;
  total_debt_outstanding: number;
  financing_cost_reduction_bps: number;
  risk_score_improvement_pct: number;
  user_adoption_rate_pct: number;
  status: string;
}

interface CaseStudy {
  id: string;
  pilot_id: string;
  title: string;
  subtitle: string;
  executive_summary: string;
  challenge: string;
  solution: string;
  results: Record<string, number>;
  status: string;
}

function formatCurrency(value: number): string {
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  return `$${value.toFixed(0)}`;
}

export default function CaseStudyGeneratorPage() {
  const [pilots, setPilots] = useState<Pilot[]>([]);
  const [selectedPilot, setSelectedPilot] = useState<Pilot | null>(null);
  const [caseStudy, setCaseStudy] = useState<CaseStudy | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<string>('summary');

  const loadPilots = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.pilotProgram.list({ status: 'active' });
      setPilots(data.pilots || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load pilots');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadPilots();
  }, [loadPilots]);

  const generateCaseStudy = useCallback(async (pilot: Pilot) => {
    setGenerating(true);
    setError(null);
    try {
      const data = await api.pilotProgram.generateCaseStudy(pilot.id);
      setCaseStudy(data.case_study);
      setSelectedPilot(pilot);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate case study');
    } finally {
      setGenerating(false);
    }
  }, []);

  const sections = [
    { id: 'summary', label: 'Executive Summary', icon: FileText },
    { id: 'challenge', label: 'Challenge', icon: Edit3 },
    { id: 'solution', label: 'Solution', icon: CheckCircle },
    { id: 'results', label: 'Results', icon: TrendingUp },
    { id: 'testimonial', label: 'Testimonial', icon: Users },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-slate-200 rounded w-1/3"></div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-48 bg-slate-200 rounded-lg"></div>
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
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
            <FileText className="w-8 h-8 text-blue-600" />
            Case Study Generator
          </h1>
          <p className="text-slate-600 mt-2">
            Generate compelling case studies from your government pilot programs.
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-600">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Pilot Selection */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Select Pilot Program</h2>
              {pilots.length === 0 ? (
                <div className="text-center py-8">
                  <Clock className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                  <p className="text-slate-600">No active pilots found.</p>
                  <p className="text-sm text-slate-500 mt-1">
                    Start a pilot program to generate case studies.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {pilots.map((pilot) => (
                    <button
                      key={pilot.id}
                      onClick={() => generateCaseStudy(pilot)}
                      disabled={generating}
                      className={`w-full p-4 rounded-lg border-2 text-left transition-colors ${
                        selectedPilot?.id === pilot.id
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">
                          {pilot.country_code === 'KE' ? '🇰🇪' :
                           pilot.country_code === 'PE' ? '🇵🇪' :
                           pilot.country_code === 'ID' ? '🇮🇩' :
                           pilot.country_code === 'GE' ? '🇬🇪' :
                           pilot.country_code === 'JO' ? '🇯🇴' :
                           '🏳️'}
                        </span>
                        <div className="flex-1">
                          <div className="font-medium text-slate-900">{pilot.country_name}</div>
                          <div className="text-sm text-slate-500">{pilot.government_entity}</div>
                          <div className="text-xs text-slate-400">
                            {formatCurrency(pilot.total_debt_outstanding)} portfolio
                          </div>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Quick Stats */}
            {selectedPilot && (
              <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200 mt-6">
                <h3 className="font-semibold text-slate-900 mb-4">Pilot Metrics</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-slate-600">Financing Cost Reduction</span>
                    <span className="font-bold text-emerald-600">
                      {selectedPilot.financing_cost_reduction_bps} bps
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-600">Risk Score Improvement</span>
                    <span className="font-bold text-emerald-600">
                      {selectedPilot.risk_score_improvement_pct}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-600">User Adoption</span>
                    <span className="font-bold text-emerald-600">
                      {selectedPilot.user_adoption_rate_pct}%
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Case Study Editor */}
          <div className="lg:col-span-2">
            {!caseStudy ? (
              <div className="bg-white rounded-xl shadow-sm p-12 border border-slate-200 text-center">
                <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-slate-900 mb-2">
                  Select a Pilot to Generate
                </h3>
                <p className="text-slate-600">
                  Choose an active pilot program from the list to generate a case study.
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Section Navigation */}
                <div className="bg-white rounded-xl shadow-sm p-4 border border-slate-200">
                  <div className="flex gap-2 overflow-x-auto">
                    {sections.map((section) => (
                      <button
                        key={section.id}
                        onClick={() => setActiveSection(section.id)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg whitespace-nowrap ${
                          activeSection === section.id
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                        }`}
                      >
                        <section.icon className="w-4 h-4" />
                        {section.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Case Study Content */}
                <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
                  {activeSection === 'summary' && (
                    <div>
                      <h2 className="text-xl font-bold text-slate-900 mb-2">{caseStudy.title}</h2>
                      <p className="text-slate-500 mb-6">{caseStudy.subtitle}</p>
                      <h3 className="font-semibold text-slate-900 mb-3">Executive Summary</h3>
                      <p className="text-slate-700 leading-relaxed">{caseStudy.executive_summary}</p>
                    </div>
                  )}

                  {activeSection === 'challenge' && (
                    <div>
                      <h3 className="font-semibold text-slate-900 mb-3">The Challenge</h3>
                      <p className="text-slate-700 leading-relaxed">{caseStudy.challenge}</p>
                    </div>
                  )}

                  {activeSection === 'solution' && (
                    <div>
                      <h3 className="font-semibold text-slate-900 mb-3">Our Solution</h3>
                      <p className="text-slate-700 leading-relaxed">{caseStudy.solution}</p>
                    </div>
                  )}

                  {activeSection === 'results' && (
                    <div>
                      <h3 className="font-semibold text-slate-900 mb-4">Results</h3>
                      <div className="grid grid-cols-2 gap-4">
                        {Object.entries(caseStudy.results).map(([key, value]) => (
                          <div key={key} className="p-4 bg-emerald-50 rounded-lg">
                            <div className="text-sm text-emerald-600 capitalize">
                              {key.replace(/_/g, ' ')}
                            </div>
                            <div className="text-2xl font-bold text-emerald-700">
                              {typeof value === 'number' && key.includes('bps')
                                ? `${value} bps`
                                : typeof value === 'number' && key.includes('pct')
                                ? `${value}%`
                                : typeof value === 'number' && value > 1000000
                                ? formatCurrency(value)
                                : value}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {activeSection === 'testimonial' && (
                    <div>
                      <h3 className="font-semibold text-slate-900 mb-3">Testimonial</h3>
                      <div className="p-6 bg-slate-50 rounded-lg border-l-4 border-blue-500">
                        <p className="text-slate-700 italic text-lg">
                          "Quantive has transformed how we manage our sovereign debt portfolio. 
                          The optimization recommendations have directly contributed to lower 
                          financing costs and better risk management."
                        </p>
                        <div className="mt-4 text-slate-600">
                          <div className="font-medium">— DMO Director</div>
                          <div className="text-sm">{selectedPilot?.country_name}</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex gap-3">
                  <button className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium flex items-center gap-2">
                    <Download className="w-4 h-4" />
                    Export as PDF
                  </button>
                  <button className="px-6 py-3 bg-slate-200 text-slate-700 rounded-lg hover:bg-slate-300 font-medium">
                    Edit Content
                  </button>
                  <button className="px-6 py-3 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 font-medium">
                    Publish
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
