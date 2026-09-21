import { useCallback, useEffect, useState } from 'react';
import {
  FileText, Plus, CheckCircle, Clock, AlertTriangle,
  ExternalLink, Download
} from 'lucide-react';
import { api } from '../api';
import type { EscrowAgreement } from '../types';

export default function EscrowPage() {
  const [agreements, setAgreements] = useState<EscrowAgreement[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState({
    depositor_name: '',
    depositor_address: '',
    depositor_contact_name: '',
    depositor_contact_email: '',
    beneficiary_name: 'Government of Example',
    beneficiary_address: '123 Government Plaza',
    beneficiary_contact_name: 'Procurement Officer',
    beneficiary_contact_email: 'procurement@example.gov',
    escrow_agent_name: 'Quantive Escrow Services',
    escrow_agent_address: '456 Trust Avenue',
    escrow_agent_contact_name: 'Escrow Agent',
    escrow_agent_contact_email: 'escrow@quantive.com',
    software_description: '',
    version: '1.0.0',
    repository_url: '',
  });

  const loadAgreements = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.escrow.listAgreements();
      setAgreements(data?.agreements || []);
    } catch (e) {
      console.error('Failed to load agreements:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAgreements();
  }, [loadAgreements]);

  const createAgreement = async () => {
    try {
      await api.escrow.createAgreement({
        depositor: {
          name: formData.depositor_name || 'Depositor',
          role: 'depositor',
          address: formData.depositor_address || '100 Default Street',
          contact_name: formData.depositor_contact_name || 'Contact',
          contact_email: formData.depositor_contact_email || 'contact@example.com',
        },
        beneficiary: {
          name: formData.beneficiary_name,
          role: 'beneficiary',
          address: formData.beneficiary_address,
          contact_name: formData.beneficiary_contact_name,
          contact_email: formData.beneficiary_contact_email,
        },
        escrow_agent: {
          name: formData.escrow_agent_name,
          role: 'escrow_agent',
          address: formData.escrow_agent_address,
          contact_name: formData.escrow_agent_contact_name,
          contact_email: formData.escrow_agent_contact_email,
        },
        software_description: formData.software_description || 'Government debt management software',
        version: formData.version || '1.0.0',
        repository_url: formData.repository_url || 'https://github.com/example/repo',
      });
      setShowCreateForm(false);
      void loadAgreements();
    } catch (e) {
      console.error('Failed to create agreement:', e);
    }
  };

  const statusColors: Record<string, string> = {
    active: 'bg-emerald-100 text-emerald-700',
    pending: 'bg-amber-100-amber text-amber-700',
    released: 'bg-blue-100 text-blue-700',
    expired: 'bg-slate-100 text-slate-700',
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
              <FileText className="w-8 h-8 text-blue-600" />
              Source Code Escrow
            </h1>
            <p className="text-slate-600 mt-2">
              Manage escrow agreements for government software deployments.
            </p>
          </div>
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" />
            New Agreement
          </button>
        </div>

        {/* Create Form */}
        {showCreateForm && (
          <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200 mb-6">
            <h2 className="font-semibold text-slate-900 mb-4">Create Escrow Agreement</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Software Name</label>
                <input
                  type="text"
                  value={formData.software_description}
                  onChange={(e) => setFormData({ ...formData, software_description: e.target.value })}
                  placeholder="Quantive Sovereign Debt Platform"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Version</label>
                <input
                  type="text"
                  value={formData.version}
                  onChange={(e) => setFormData({ ...formData, version: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Repository URL</label>
                <input
                  type="text"
                  value={formData.repository_url}
                  onChange={(e) => setFormData({ ...formData, repository_url: e.target.value })}
                  placeholder="https://github.com/quantive/..."
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Depositor Name</label>
                <input
                  type="text"
                  value={formData.depositor_name}
                  onChange={(e) => setFormData({ ...formData, depositor_name: e.target.value })}
                  placeholder="Quantive Inc."
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Depositor Contact</label>
                <input
                  type="text"
                  value={formData.depositor_contact_name}
                  onChange={(e) => setFormData({ ...formData, depositor_contact_name: e.target.value })}
                  placeholder="John Smith"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Depositor Email</label>
                <input
                  type="email"
                  value={formData.depositor_contact_email}
                  onChange={(e) => setFormData({ ...formData, depositor_contact_email: e.target.value })}
                  placeholder="john@quantive.com"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => setShowCreateForm(false)}
                className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={createAgreement}
                disabled={!formData.software_description || !formData.depositor_name}
                className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm"
              >
                Create Agreement
              </button>
            </div>
          </div>
        )}

        {/* Agreement List */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200">
          {loading ? (
            <div className="p-12 text-center">
              <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto"></div>
              <p className="text-slate-500 mt-4">Loading agreements...</p>
            </div>
          ) : agreements.length === 0 ? (
            <div className="p-12 text-center">
              <FileText className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 mb-2">No escrow agreements</h3>
              <p className="text-slate-500 mb-4">Create your first escrow agreement for government deployment.</p>
              <button
                onClick={() => setShowCreateForm(true)}
                className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
              >
                <Plus className="w-4 h-4" />
                Create Agreement
              </button>
            </div>
          ) : (
            <div className="divide-y divide-slate-200">
              {agreements.map(agreement => (
                <div key={agreement.id} className="p-4 hover:bg-slate-50">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                        <FileText className="w-5 h-5 text-blue-600" />
                      </div>
                      <div>
                        <div className="font-medium text-slate-900">{agreement.name}</div>
                        <div className="text-sm text-slate-500">
                          {agreement.version ? `v${agreement.version}` : 'No version'}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[agreement.status] || 'bg-slate-100 text-slate-700'}`}>
                        {agreement.status}
                      </span>
                      <div className="text-right">
                        <div className="text-xs text-slate-500">
                          Created: {new Date(agreement.created_at).toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
