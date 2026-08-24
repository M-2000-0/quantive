import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import type { OptimizationJob, Report } from '../types';
import AppShell from '../components/layout/AppShell';
import Card, { CardHeader } from '../components/ui/Card';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import EmptyState from '../components/ui/EmptyState';
import { formatDateTime } from '../utils';
import { useToast } from '../components/Toast';

const REPORT_SECTIONS = [
  { label: 'Executive Summary', icon: '\u2713' },
  { label: 'Portfolio Overview', icon: '\u2713' },
  { label: 'Objectives & Constraints', icon: '\u2713' },
  { label: 'Scenario Analysis', icon: '\u2713' },
  { label: 'Optimization Results', icon: '\u2713' },
  { label: 'Strategy Comparison', icon: '\u2713' },
  { label: 'Stress Testing', icon: '\u2713' },
  { label: 'Benchmarks', icon: '\u2713' },
  { label: 'Methodology Notes', icon: '\u2713' },
  { label: 'Audit Trail', icon: '\u2713' },
];

function downloadReport(report: Report) {
  const sections: string[] = [];
  sections.push(`# Quantive Decision Report`);
  sections.push(`\n## Job: ${report.job_name}`);
  sections.push(`Status: ${report.status}`);
  sections.push(`Type: ${report.optimization_type.replace(/_/g, ' ')}`);
  sections.push(`Created: ${report.created_at}`);
  sections.push(`Completed: ${report.completed_at || 'N/A'}`);
  sections.push(`Model Version: ${report.model_version}`);
  sections.push(`Random Seed: ${report.random_seed}`);

  sections.push(`\n## Portfolio`);
  sections.push(`Name: ${report.portfolio.name}`);
  sections.push(`Instruments: ${report.portfolio.num_instruments}`);

  sections.push(`\n## Strategies`);
  for (const s of report.strategies) {
    sections.push(`\n### ${s.name} (Rank #${s.rank})`);
    sections.push(s.description);
    sections.push(`Metrics: ${JSON.stringify(s.metrics, null, 2)}`);
    if (s.stress_test_results) {
      sections.push(`Stress Test: ${JSON.stringify(s.stress_test_results, null, 2)}`);
    }
  }

  sections.push(`\n## Benchmarks`);
  for (const b of report.benchmarks) {
    sections.push(`- ${b.solver_name}: objective=${b.objective_value}, feasible=${b.feasible}, time=${b.execution_time_seconds.toFixed(1)}s, iterations=${b.iterations}`);
  }

  sections.push(`\n## Summary`);
  sections.push(JSON.stringify(report.summary, null, 2));

  const blob = new Blob([sections.join('\n')], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `quantive-report-${report.job_id.slice(0, 8)}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ReportsPage() {
  const [jobs, setJobs] = useState<OptimizationJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState<string | null>(null);
  const { addToast } = useToast();

  useEffect(() => {
    api.optimizations
      .list()
      .then((res) => setJobs((res as { data: OptimizationJob[] }).data || []))
      .catch(() => setJobs([]))
      .finally(() => setLoading(false));
  }, []);

  const completedJobs = jobs.filter((j) => j.status === 'completed');

  const handleDownload = async (jobId: string) => {
    setGenerating(jobId);
    try {
      const report = await api.optimizations.report(jobId);
      downloadReport(report);
      addToast('Report downloaded', 'success');
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : 'Failed to generate report', 'error');
    } finally {
      setGenerating(null);
    }
  };

  if (loading) {
    return (
      <AppShell>
        <LoadingSpinner message="Loading reports..." />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="px-8 py-6 max-w-[1440px] mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900">Decision Reports</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Generate and export decision packages for completed optimizations
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
          <div className="xl:col-span-2">
            <Card padding={false}>
              <div className="px-6 py-4 border-b border-slate-200">
                <h3 className="text-base font-semibold text-slate-900">Available Reports</h3>
                <p className="text-sm text-slate-500 mt-0.5">
                  {completedJobs.length} completed optimization{completedJobs.length !== 1 ? 's' : ''}
                </p>
              </div>

              {completedJobs.length === 0 ? (
                <div className="px-6 py-16">
                  <EmptyState
                    icon={
                      <svg className="h-12 w-12" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                      </svg>
                    }
                    title="No reports available"
                    description="Complete an optimization to generate a decision package."
                  />
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {completedJobs.map((job) => (
                    <div
                      key={job.id}
                      className="flex items-center justify-between px-6 py-5 hover:bg-slate-50 transition-colors"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-3">
                          <h4 className="text-sm font-semibold text-slate-900">{job.name}</h4>
                          <Badge variant="success">Completed</Badge>
                        </div>
                        <div className="mt-1 flex items-center gap-4 text-xs text-slate-500">
                          <span>Generated {formatDateTime(job.completed_at || job.created_at)}</span>
                          <span>&middot;</span>
                          <span>{job.optimization_type.replace(/_/g, ' ')}</span>
                          <span>&middot;</span>
                          <span>Seed {job.random_seed}</span>
                        </div>
                      </div>
                      <div className="ml-4 flex items-center gap-2">
                        <Link to={`/optimizations/${job.id}`}>
                          <Button variant="secondary" size="sm">View Report</Button>
                        </Link>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDownload(job.id)}
                          disabled={generating === job.id}
                        >
                          {generating === job.id ? 'Generating...' : 'Export'}
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          <div>
            <Card>
              <CardHeader
                title="Decision Package"
                subtitle="Compile all analysis into a single document"
              />
              <div className="space-y-2.5">
                {REPORT_SECTIONS.map((section) => (
                  <div key={section.label} className="flex items-center gap-3 text-sm">
                    <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 text-xs font-bold flex-shrink-0">
                      {section.icon}
                    </span>
                    <span className="text-slate-700">{section.label}</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
