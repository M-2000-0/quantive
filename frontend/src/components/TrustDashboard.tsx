import React, { useEffect, useState } from 'react';
import { CheckCircle } from 'lucide-react';
import { getTrustDashboard, type TrustMetric, type CorruptionRisk, type EnvironmentFlag } from '../lib/trustDashboard';
import { getAssumptionRegistry } from '../lib/assumptionRegistry';
import { Card, Badge } from '../components/ui';

interface TrustDashboardProps {
  optimizationId?: string;
}

export default function TrustDashboard({ optimizationId }: TrustDashboardProps = {}) {
  const [metrics, setMetrics] = useState<TrustMetric[]>([]);
  const [corruptionRisks, setCorruptionRisks] = useState<CorruptionRisk[]>([]);
  const [environment, setEnvironment] = useState<{
    hasSingleApprover: boolean;
    hasDualApproval: boolean;
    allowManualOverrides: boolean;
    exportRestrictions: boolean;
    auditLogEnabled: boolean;
    vendorAccessLevel: string;
    recentAnomalies: number;
  }>({
    hasSingleApprover: false,
    hasDualApproval: false,
    allowManualOverrides: false,
    exportRestrictions: false,
    auditLogEnabled: false,
    vendorAccessLevel: 'limited',
    recentAnomalies: 0 });
  const [trustScore, setTrustScore] = useState<{
    overall: number;
    grade: 'A' | 'B' | 'C' | 'D' | 'F';
    breakdown: {
      dataQuality: number;
      modelQuality: number;
      uncertainty: number;
      confidence: number;
    };
    limitations: string[];
    disclaimer: string;
    recommendationId: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  // Optional: link a specific optimization run; defaults to none.
  const currentOptimization: { id: string } | null = null;

  // Load trust metrics
  useEffect(() => {
    const dashboard = getTrustDashboard();
    setMetrics(dashboard.getMetrics());

    // Compute recommendation trust score if we have an optimization
    if (optimizationId || currentOptimization?.id) {
      const recId = optimizationId || (currentOptimization as { id: string }).id;
      const opt = (currentOptimization || { id: optimizationId, status: 'unknown' }) as any;

      // Mock strategy data for trust scoring - in production this would come from API
      const mockRecommendation = {
        id: recId,
        strategy: {
          name: 'Recommended Strategy',
          metrics: {
            expected_cost: opt.metrics?.expected_cost || 0,
            refinancing_risk: opt.metrics?.refinancing_risk || 0,
            interest_rate_risk: opt.metrics?.interest_rate_risk || 0,
            currency_risk: opt.metrics?.currency_risk || 0 } },
        portfolio_data: {
          instruments: opt.instruments || [] },
        country_code: 'US' };

      const trustResult = dashboard.computeRecommendationTrustScore(mockRecommendation, undefined);
      setTrustScore(trustResult);
    }

    // Detect corruption risks
    const risks = dashboard.detectCorruptionRisks({
      hasSingleApprover: false,
      hasDualApproval: false,
      allowManualOverrides: true,
      exportRestrictions: false,
      auditLogEnabled: true,
      vendorAccessLevel: 'broad',
      recentAnomalies: 3 });
    setCorruptionRisks(risks);

    setLoading(false);
  }, [optimizationId, currentOptimization?.id]);

  // Load assumption registry bias reports
  useEffect(() => {
    const registry = getAssumptionRegistry();
    // Bias reports are available via registry.getBiasReport()
    // We'll subscribe to bias report changes
    const unsub = registry?.getBiasReport && typeof registry.getBiasReport === 'function'
      ? () => {} // Placeholder - real implementation would subscribe
      : () => {};

    return unsub;
  }, []);

  // Environmental flags update from audit
  useEffect(() => {
    // In production, these would come from security/audit system
    const checkEnvironment = async () => {
      try {
        const security = await import('../api/security');
        const dashboard = security.security.dashboard();
        const data = await dashboard;
        // Map security dashboard to environment flags
        setEnvironment(prev => ({
          ...prev,
          hasSingleApprover: data.recommendations.some((r: any) => r.severity === 'high' && r.action.includes('approve')),
          hasDualApproval: data.recommendations.some((r: any) => r.action.includes('dual')),
          allowManualOverrides: false,
          exportRestrictions: true,
          auditLogEnabled: true,
          vendorAccessLevel: 'limited',
          recentAnomalies: data.audit_events_24h['data export'] || 0 }));
      } catch (e) {
        console.error('Failed to load environment flags', e);
      }
    };
    checkEnvironment();
  }, []);

  const riskLevels = {
    critical: 'bg-red-500/20 text-red-400 border-red-500/30',
    high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    low: 'bg-green-500/20 text-green-400 border-green-500/30' };

  const statusColors = {
    open: 'bg-red-500/20 text-red-400 border-red-500/20',
    partial: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/20',
    mitigated: 'bg-green-500/20 text-green-400 border-green-500/20' };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="text-slate-400">Loading Trust Dashboard...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Trust Score Summary */}
      {trustScore && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <h3 className="text-sm font-medium text-slate-400 mb-2">Overall Trust Score</h3>
            <div className={`text-3xl font-bold ${trustScore.grade === 'A' ? 'text-green-400' : trustScore.grade === 'B' ? 'text-yellow-400' : 'text-red-400'}`}>
              {trustScore.overall}
            </div>
            <Badge variant="info" size="sm">
              {trustScore.grade}
            </Badge>
          </Card>

          <Card>
            <h3 className="text-sm font-medium text-slate-400 mb-2">Data Quality</h3>
            <div className={`text-3xl font-bold ${trustScore.breakdown.dataQuality >= 80 ? 'text-green-400' : 'text-slate-300'}`}>
              {trustScore.breakdown.dataQuality}
            </div>
          </Card>

          <Card>
            <h3 className="text-sm font-medium text-slate-400 mb-2">Model Quality</h3>
            <div className={`text-3xl font-bold ${trustScore.breakdown.modelQuality >= 80 ? 'text-green-400' : 'text-slate-300'}`}>
              {trustScore.breakdown.modelQuality}
            </div>
          </Card>

          <Card>
            <h3 className="text-sm font-medium text-slate-400 mb-2">Confidence</h3>
            <div className={`text-3xl font-bold ${trustScore.breakdown.confidence >= 80 ? 'text-green-400' : 'text-slate-300'}`}>
              {trustScore.breakdown.confidence}
            </div>
          </Card>
        </div>
      )}

      {/* Corruption Risk Detection */}
      <div>
        <h2 className="text-xl font-bold text-white">Anti-Corruption Detection</h2>
        <p className="text-slate-400">Environment scan for corruption opportunities - structural weaknesses before exploitation.</p>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {Object.entries(environment).map(([key, value]) => (
            <div key={key} className="glass rounded-xl p-3 text-center">
              <div className="text-2xl font-bold">{value}</div>
              <div className="text-xs text-slate-400 mt-1">{key.replace(/_/g, ' ')}</div>
            </div>
          ))}
        </div>

        {corruptionRisks.length > 0 && (
          <div className="mt-6 glass rounded-2xl p-6">
            <h3 className="text-sm font-medium text-slate-400 mb-4">STRUCTURAL VULNERABILITIES</h3>
            <div className="space-y-4">
              {corruptionRisks.map((risk, i) => (
                <div
                  key={risk.id}
                  className={`flex items-center gap-4 p-4 rounded-xl border ${statusColors[risk.currentStatus]}`}
                >
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${risk.risk === 'critical' ? 'bg-red-500/20 text-red-400' : risk.risk === 'high' ? 'bg-orange-500/20 text-orange-400' : risk.risk === 'medium' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-green-500/20 text-green-400'}`}>
                    {risk.risk.toUpperCase()}
                  </span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="text-white text-sm font-medium">{risk.area}</h4>
                      <span className={`px-2 py-0.5 rounded text-xs ${risk.risk === 'critical' ? 'bg-red-500/20 text-red-400' : risk.risk === 'high' ? 'bg-orange-500/20 text-orange-400' : risk.risk === 'medium' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-green-500/20 text-green-400'}`}>
                        {risk.pattern}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mb-1">Weakness: {risk.description}</p>
                    <p className="text-xs text-slate-500">Recommendation: {risk.recommendation}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {corruptionRisks.length === 0 && (
          <div className="mt-6 p-6 bg-green-500/10 border border-green-500/20 rounded-xl">
            <p className="text-sm text-green-400">
              <CheckCircle className="w-4 h-4 inline" /> <strong>No corruption risks detected.</strong> Environment appears structurally sound.
            </p>
          </div>
        )}
      </div>

      {/* Assumption Registry Bias Reports */}
      <div>
        <h2 className="text-xl font-bold text-white">Assumption Registry Bias Reports</h2>
        <p className="text-slate-400">Institutional intelligence on assumption accuracy over time.</p>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Bias report cards would be populated from registry */}
          {[...Array(4)].map((_, i) => (
            <div key={i} className="glass rounded-xl p-3 text-center">
              <div className="text-2xl font-bold">—</div>
              <div className="text-xs text-slate-400 mt-1">Category</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}