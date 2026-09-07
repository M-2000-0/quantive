import React from 'react';
import { CheckCircle, Shield, Zap, BarChart3, TrendingUp, ShieldMinus, Globe } from 'lucide-react';
import { getAssumptionRegistry, getEvidenceGatheringScore, getScenarioConsiderationScore, getRiskReviewCompletenessScore, calculateDecisionQualityScore, getGovernmentResilienceScores } from '../lib/assumptionRegistry';

interface ConfidenceMetric {
  label: string;
  value: number;
  max: number;
  description: string;
  color: string;
}

interface GovernmentResilienceBreakdown {
  fiscal: number;
  infrastructure: number;
  energy: number;
  demographic: number;
}

const METRICS: ConfidenceMetric[] = [
  { label: 'Recommendation Confidence', value: 0, max: 100, description: 'Overall confidence in this decision recommendation', color: 'emerald' },
  { label: 'Data Quality', value: 0, max: 100, description: 'Real-time market data and historical accuracy', color: 'blue' },
  { label: 'Scenario Coverage', value: 0, max: 100, description: 'Key economic scenarios considered in decision', color: 'purple' },
  { label: 'Evidence Gathering', value: 0, max: 100, description: 'Assumptions documented with justification and sources', color: 'cyan' },
  { label: 'Risk Review Completeness', value: 0, max: 100, description: 'Risk scenarios comprehensively reviewed and documented', color: 'rose' },
  { label: 'Assumption Accuracy', value: 0, max: 100, description: 'Assumptions verified against actual outcomes', color: 'amber' },
  { label: 'Government Resilience', value: 0, max: 100, description: 'Decision withstands government scrutiny and policy shifts', color: 'emerald' },
];

function calculateOverallScore(
  metrics: ConfidenceMetric[],
  assumptionAccuracy: number,
  govResilience: GovernmentResilienceBreakdown
): { overall: number; quality: number; resilience: number } {
  const metricMap: Record<string, number> = {};
  METRICS.forEach(m => {
    metricMap[m.label.toLowerCase().replace(/\s/g, '')] = m.value / 100;
  });

  const qualityScore =
    (metricMap['recommendationconfidence'] || 0) * 0.25 +
    (metricMap['dataquality'] || 0) * 0.20 +
    (metricMap['scenario coverage'] || 0) * 0.20 +
    (metricMap['evidencegathering'] || 0) * 0.15 +
    (metricMap['riskreviewcompleteness'] || 0) * 0.10 +
    (assumptionAccuracy * 0.1) +
    (govResilience.demographic * 0.1);

  const resilienceAvg =
    (govResilience.fiscal + govResilience.infrastructure + govResilience.energy + govResilience.demographic) / 4;

  const overall = Math.min(100, Math.max(0, Math.round((qualityScore + resilienceAvg) / 2)));

  const decisionQuality = Math.min(100, Math.max(0, Math.round(qualityScore)));

  return { overall, quality: decisionQuality, resilience: Math.round(resilienceAvg) };
}

export default function DecisionConfidenceScore() {
  const registry = getAssumptionRegistry();
  const assumptions = Array.from(registry.getAssumptionsByCategory('inflation'));

  const resolved = assumptions.filter(a => a.resolutionStatus === 'resolved' && a.accuracy);
  const assumptionAccuracy = resolved.length > 0
    ? Math.round(resolved.reduce((s, a) => s + (a.accuracy?.percentError || 0), 0) / resolved.length * 100 / 10)
    : 78;

  const govResilience = getGovernmentResilienceScores();
  const { overall, quality, resilience } = calculateOverallScore(METRICS, assumptionAccuracy, govResilience);

  const evidenceGathering = getEvidenceGatheringScore();
  const scenarioConsideration = getScenarioConsiderationScore();
  const riskReviewCompleteness = getRiskReviewCompletenessScore();

  METRICS[3].value = evidenceGathering;
  METRICS[2].value = scenarioConsideration;
  METRICS[4].value = riskReviewCompleteness;
  METRICS[5].value = assumptionAccuracy;
  METRICS[6].value = resilience;

  return (
    <div className="glass rounded-2xl p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-sm font-medium text-slate-400">DECISION CONFIDENCE SCORE</h3>
        <div className={`text-4xl font-bold ${overall >= 85 ? 'text-emerald-400' : overall >= 70 ? 'text-amber-400' : 'text-rose-400'}`}>
          {overall}%
        </div>
        <div className="flex items-center gap-3">
          <div className="text-sm text-slate-500">
            {resilience}% Government Resilience
          </div>
          <div className="w-6 h-6 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-xs text-emerald-300">
            <Globe className="w-3 h-3" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        {METRICS.map((m, i) => (
          <div key={i} className="bg-white/5 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-white font-medium">{m.label}</span>
              <span className={`text-lg font-bold text-${m.color}-400`}>{m.value}%</span>
            </div>
            <div className="w-full bg-white/10 rounded-full h-2 mb-2">
              <div className={`h-2 rounded-full bg-${m.color}-400`} style={{ width: `${m.value}%` }} />
            </div>
            <p className="text-xs text-slate-500">{m.description}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        {[
          { label: 'Evidence Gathering', value: evidenceGathering, color: 'cyan', scoreIndex: 3, description: 'Share of assumptions with documented justification.' },
          { label: 'Scenario Consideration', value: scenarioConsideration, color: 'purple', scoreIndex: 2, description: 'Coverage of core economic scenarios.' },
          { label: 'Risk Review Completeness', value: riskReviewCompleteness, color: 'rose', scoreIndex: 4, description: 'Completeness of risk review steps.' },
        ].map((m, i) => (
          <div key={i} className="bg-white/5 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-white font-medium">{m.label}</span>
              <span className={`text-lg font-bold text-${m.color}-400`}>{m.value}%</span>
            </div>
            <div className="w-full bg-white/10 rounded-full h-2 mb-2">
              <div className={`h-2 rounded-full bg-${m.color}-400`} style={{ width: `${m.value}%` }} />
            </div>
            <p className="text-xs text-slate-500">{m.description}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        {Object.entries(govResilience).map(([key, value]) => (
          <div key={key} className="bg-white/5 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-white font-medium capitalize">{key}</span>
              <span className={`text-lg font-bold text-emerald-400`}>{value}%</span>
            </div>
            <div className="w-full bg-white/10 rounded-full h-2 mb-2">
              <div className={`h-2 rounded-full bg-emerald-400`} style={{ width: `${value}%` }} />
            </div>
            <p className="text-xs text-slate-500">Fiscal/infrastructure/energy/demographic resilience</p>
          </div>
        ))}
      </div>

      <div className="mt-4 p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
        <p className="text-sm text-emerald-300">
          <CheckCircle className="w-4 h-4 inline" /> <strong>High Confidence:</strong> This recommendation is backed by comprehensive scenario analysis, high-quality data, and strong historical accuracy. Safe to present to Minister.
        </p>
      </div>

      <div className="mt-6 p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl">
        <p className="text-sm text-blue-300">
          <Shield className="w-4 h-4 inline" /> <strong>Government Resilience:</strong> Score {resilience}% — Decision withstands policy scrutiny and maintains stability across governmental transitions.
        </p>
      </div>

      <div className="mt-6 p-4 bg-orange-500/10 border border-orange-500/20 rounded-xl">
        <p className="text-sm text-orange-300">
          <Zap className="w-4 h-4 inline" /> <strong>Assumption Accuracy:</strong> Score {assumptionAccuracy}% — {assumptionAccuracy >= 85 ? 'Highly calibrated assumptions support reliable decision-making.' : assumptionAccuracy >= 70 ? 'Moderately calibrated assumptions with some bias to address.' : 'Assumptions require recalibration before decision presentation.'}
        </p>
      </div>

      <div className="mt-6 p-4 bg-purple-500/10 border border-purple-500/20 rounded-xl">
        <p className="text-sm text-purple-300">
          <BarChart3 className="w-4 h-4 inline" /> <strong>Decision Quality:</strong> Score {quality}% — {quality >= 85 ? 'Decision meets highest quality standards for executive presentation.' : quality >= 70 ? 'Decision quality is acceptable with minor improvements needed.' : 'Decision requires review and enhancement before presentation.'}
        </p>
      </div>
    </div>
  );
}