import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle, Shield, Play, CheckCircle, Clock,
  Database, RefreshCw, Plus
} from 'lucide-react';
import { api } from '../api';

interface Backup {
  backup_id: string;
  type: string;
  timestamp: string;
  location: string;
  size_bytes: number;
  encrypted: boolean;
  verified: boolean;
}

interface DRTest {
  test_id: string;
  test_type: string;
  status: string;
  rto_achieved_minutes: number;
  rpo_achieved_minutes: number;
  started_at: string;
  completed_at: string;
}

export default function DisasterRecoveryPage() {
  const [status, setStatus] = useState<any>(null);
  const [backups, setBackups] = useState<Backup[]>([]);
  const [tests, setTests] = useState<DRTest[]>([]);
  const [compliance, setCompliance] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [creatingBackup, setCreatingBackup] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [statusData, backupsData, complianceData] = await Promise.all([
        api.disasterRecovery.status().catch(() => null),
        api.disasterRecovery.listBackups(20).catch(() => ({ backups: [] })),
        api.disasterRecovery.getComplianceChecklist().catch(() => null),
      ]);

      if (statusData) setStatus(statusData);
      if (backupsData?.backups) setBackups(backupsData.backups);
      if (complianceData) setCompliance(complianceData);
    } catch (e) {
      console.error('Failed to load DR data:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const createBackup = async (type: string) => {
    setCreatingBackup(true);
    try {
      await api.disasterRecovery.createBackup(type);
      void loadData();
    } catch (e) {
      console.error('Backup failed:', e);
    } finally {
      setCreatingBackup(false);
    }
  };

  const runTest = async (type: string) => {
    try {
      await api.disasterRecovery.runTest(type);
      void loadData();
    } catch (e) {
      console.error('DR test failed:', e);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} GB`;
    if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(1)} MB`;
    return `${(bytes / 1e3).toFixed(1)} KB`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-slate-200 rounded w-1/3"></div>
            <div className="h-64 bg-slate-200 rounded-lg"></div>
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
              <AlertTriangle className="w-8 h-8 text-red-600" />
              Disaster Recovery
            </h1>
            <p className="text-slate-600 mt-2">
              Backup management, DR testing, and compliance monitoring.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => createBackup('full')}
              disabled={creatingBackup}
              className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {creatingBackup ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              Create Backup
            </button>
            <button
              onClick={() => runTest('full_recovery')}
              className="flex items-center gap-2 bg-amber-600 text-white px-4 py-2 rounded-lg hover:bg-amber-700"
            >
              <Play className="w-4 h-4" />
              Run DR Test
            </button>
          </div>
        </div>

        {/* Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-emerald-100 rounded-lg flex items-center justify-center">
                <CheckCircle className="w-6 h-6 text-emerald-600" />
              </div>
              <div>
                <div className="text-sm text-slate-500">Status</div>
                <div className="text-lg font-bold text-emerald-600 capitalize">{status?.status || 'Unknown'}</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <Database className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <div className="text-sm text-slate-500">Backups</div>
                <div className="text-2xl font-bold text-slate-900">{status?.total_backups || 0}</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-emerald-100 rounded-lg flex items-center justify-center">
                <Shield className="w-6 h-6 text-emerald-600" />
              </div>
              <div>
                <div className="text-sm text-slate-500">Verified</div>
                <div className="text-2xl font-bold text-slate-900">{status?.verified_backups || 0}</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-amber-100 rounded-lg flex items-center justify-center">
                <Clock className="w-6 h-6 text-amber-600" />
              </div>
              <div>
                <div className="text-sm text-slate-500">DR Tests</div>
                <div className="text-2xl font-bold text-slate-900">{status?.total_tests || 0}</div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Backup History */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200">
            <div className="p-4 border-b border-slate-200">
              <h2 className="font-semibold text-slate-900">Backup History</h2>
            </div>
            <div className="divide-y divide-slate-200 max-h-96 overflow-y-auto">
              {backups.length === 0 ? (
                <div className="p-6 text-center text-slate-500">No backups yet</div>
              ) : (
                backups.map(backup => (
                  <div key={backup.backup_id} className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium text-slate-900 text-sm">{backup.type} backup</div>
                        <div className="text-xs text-slate-500">
                          {new Date(backup.timestamp).toLocaleString()} • {formatBytes(backup.size_bytes)}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {backup.encrypted && <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded">Encrypted</span>}
                        {backup.verified ? (
                          <CheckCircle className="w-4 h-4 text-emerald-500" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-amber-500" />
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Compliance Checklist */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200">
            <div className="p-4 border-b border-slate-200">
              <h2 className="font-semibold text-slate-900">DR Compliance</h2>
            </div>
            <div className="p-6">
              {compliance ? (
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-sm text-slate-500">Compliance Score</span>
                    <span className="font-bold text-lg text-slate-900">{compliance.compliance_score}%</span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-3 mb-6">
                    <div
                      className={`h-3 rounded-full ${compliance.compliance_score >= 80 ? 'bg-emerald-500' : compliance.compliance_score >= 50 ? 'bg-amber-500' : 'bg-red-500'}`}
                      style={{ width: `${compliance.compliance_score}%` }}
                    ></div>
                  </div>
                  <div className="space-y-2">
                    {compliance.checklist?.slice(0, 5).map((item: any, idx: number) => (
                      <div key={idx} className="flex items-center gap-2 text-sm">
                        <CheckCircle className="w-4 h-4 text-emerald-500" />
                        <span className="text-slate-700">{item.item}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-center text-slate-500">Loading compliance data...</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
