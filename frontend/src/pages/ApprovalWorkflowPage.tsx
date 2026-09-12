import { useCallback, useEffect, useState } from 'react';
import {
  CheckCircle, XCircle, Clock, Users, AlertTriangle,
  Plus, RefreshCw, ChevronDown, ChevronUp
} from 'lucide-react';
import { api } from '../api';
import type { ApprovalRequest } from '../types';

export default function ApprovalWorkflowPage() {
  const [requests, setRequests] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('pending');
  const [expandedRequest, setExpandedRequest] = useState<string | null>(null);
  const [approveComment, setApproveComment] = useState('');

  const loadRequests = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.approvalWorkflow.pending();
      setRequests(
        filter === 'pending'
          ? (data || [])
          : (data || []).filter(r => r.status === filter)
      );
    } catch (e) {
      console.error('Failed to load approval requests:', e);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    void loadRequests();
  }, [loadRequests]);

  const handleApprove = async (requestId: string) => {
    try {
      await api.approvalWorkflow.approve(requestId, { comments: approveComment || 'Approved' });
      setApproveComment('');
      setExpandedRequest(null);
      void loadRequests();
    } catch (e) {
      console.error('Approval failed:', e);
    }
  };

  const handleDeny = async (requestId: string) => {
    try {
      await api.approvalWorkflow.deny(requestId, { reason: approveComment || 'Denied', comments: approveComment || 'Denied' });
      setApproveComment('');
      setExpandedRequest(null);
      void loadRequests();
    } catch (e) {
      console.error('Denial failed:', e);
    }
  };

  const statusColors: Record<string, string> = {
    pending: 'bg-amber-100 text-amber-700',
    approved: 'bg-emerald-100 text-emerald-700',
    denied: 'bg-red-100 text-red-700',
    cancelled: 'bg-slate-100 text-slate-700',
    expired: 'bg-orange-100 text-orange-700',
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
              <Users className="w-8 h-8 text-blue-600" />
              Approval Workflow
            </h1>
            <p className="text-slate-600 mt-2">
              Multi-level approval enforcement with separation of duties.
            </p>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex gap-2 mb-6">
          {['pending', 'approved', 'denied', 'cancelled'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
                filter === f
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-slate-600 hover:bg-slate-50 border border-slate-200'
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        {/* Request List */}
        <div className="space-y-4">
          {loading ? (
            <div className="bg-white rounded-xl shadow-sm p-12 border border-slate-200 text-center">
              <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto"></div>
              <p className="text-slate-500 mt-4">Loading approval requests...</p>
            </div>
          ) : requests.length === 0 ? (
            <div className="bg-white rounded-xl shadow-sm p-12 border border-slate-200 text-center">
              <CheckCircle className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 mb-2">No {filter} requests</h3>
              <p className="text-slate-500">
                {filter === 'pending' ? 'All requests have been reviewed.' : `No ${filter} requests found.`}
              </p>
            </div>
          ) : (
            requests.map(req => (
              <div
                key={req.id}
                className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden"
              >
                <div
                  className="p-4 cursor-pointer hover:bg-slate-50"
                  onClick={() => setExpandedRequest(expandedRequest === req.id ? null : req.id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`px-2 py-1 rounded text-xs font-medium ${statusColors[req.status]}`}>
                        {req.status}
                      </div>
                      <div>
                        <div className="font-medium text-slate-900">{req.type}</div>
                        <div className="text-sm text-slate-500">
                          {String((req.data as Record<string, unknown>)?.resource_type || req.type)}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className="text-sm text-slate-500">Requester: {req.requested_by}</div>
                        <div className="text-xs text-slate-400">
                          {new Date(req.created_at).toLocaleString()}
                        </div>
                      </div>
                      {expandedRequest === req.id ? (
                        <ChevronUp className="w-5 h-5 text-slate-400" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-slate-400" />
                      )}
                    </div>
                  </div>
                </div>

                {/* Expanded Actions */}
                {expandedRequest === req.id && req.status === 'pending' && (
                  <div className="border-t border-slate-200 p-4 bg-slate-50">
                    <div className="mb-4">
                      <label className="block text-sm font-medium text-slate-700 mb-1">Comment</label>
                      <textarea
                        value={approveComment}
                        onChange={(e) => setApproveComment(e.target.value)}
                        placeholder="Add a comment..."
                        className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
                        rows={2}
                      />
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleApprove(req.id)}
                        className="flex items-center gap-2 bg-emerald-600 text-white px-4 py-2 rounded-lg hover:bg-emerald-700 text-sm"
                      >
                        <CheckCircle className="w-4 h-4" />
                        Approve
                      </button>
                      <button
                        onClick={() => handleDeny(req.id)}
                        className="flex items-center gap-2 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 text-sm"
                      >
                        <XCircle className="w-4 h-4" />
                        Deny
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
