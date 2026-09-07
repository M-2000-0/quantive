// ── Approval Workflow Component ───────────────────────────────────────
// Manages the approval pipeline for optimization decisions.
// Tracks status through: Draft → Submitted → Under Review → Approved/Rejected → Executed.

import { useState } from 'react';
import type { DecisionEntry, DecisionStatus } from '../lib/decisionJournal';

interface WorkflowStep {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'completed' | 'rejected';
  assignee?: string;
  completedAt?: number | string;
  notes?: string;
}

interface ApprovalWorkflowProps {
  decision: DecisionEntry;
  onStatusChange?: (status: DecisionStatus, notes?: string) => void;
}

const STATUS_FLOW: DecisionStatus[] = ['recommended', 'approved', 'executed', 'completed'];

const STATUS_STYLES: Record<DecisionStatus, { bg: string; text: string; ring: string }> = {
  draft: { bg: 'bg-slate-50', text: 'text-slate-500', ring: 'ring-slate-200' },
  submitted: { bg: 'bg-blue-50', text: 'text-blue-700', ring: 'ring-blue-200' },
  under_review: { bg: 'bg-amber-50', text: 'text-amber-700', ring: 'ring-amber-200' },
  recommended: { bg: 'bg-blue-50', text: 'text-blue-700', ring: 'ring-blue-200' },
  approved: { bg: 'bg-emerald-50', text: 'text-emerald-700', ring: 'ring-emerald-200' },
  executed: { bg: 'bg-purple-50', text: 'text-purple-700', ring: 'ring-purple-200' },
  completed: { bg: 'bg-green-50', text: 'text-green-700', ring: 'ring-green-200' },
  rejected: { bg: 'bg-red-50', text: 'text-red-700', ring: 'ring-red-200' },
  expired: { bg: 'bg-slate-50', text: 'text-slate-500', ring: 'ring-slate-200' } };

function getWorkflowSteps(decision: DecisionEntry): WorkflowStep[] {
  const steps: WorkflowStep[] = [
    {
      id: 'draft',
      label: 'Recommendation Generated',
      status: 'completed',
      completedAt: decision.timestamp,
      notes: `Confidence: ${decision.recommendation.confidence}%` },
    {
      id: 'submit',
      label: 'Submitted for Review',
      status: decision.decision.status !== 'recommended' ? 'completed' : 'active',
      assignee: decision.decision.decidedBy,
      completedAt: decision.decision.decidedAt },
    {
      id: 'review',
      label: 'Under Review',
      status: decision.decision.status === 'recommended' ? 'active' :
        ['approved', 'executed', 'completed'].includes(decision.decision.status) ? 'completed' :
        decision.decision.status === 'rejected' ? 'rejected' : 'pending',
      assignee: decision.decision.decidedBy,
      notes: decision.decision.reason },
    {
      id: 'approve',
      label: 'Decision',
      status: decision.decision.status === 'recommended' ? 'pending' :
        decision.decision.status === 'rejected' ? 'rejected' :
        ['approved', 'executed', 'completed'].includes(decision.decision.status) ? 'completed' : 'pending',
      assignee: decision.decision.decidedBy,
      completedAt: decision.decision.decidedAt,
      notes: decision.decision.overrideNotes || decision.decision.reason },
    {
      id: 'execute',
      label: 'Execution',
      status: decision.decision.status === 'executed' || decision.decision.status === 'completed' ? 'completed' :
        decision.decision.status === 'approved' ? 'active' : 'pending' },
    {
      id: 'complete',
      label: 'Completed',
      status: decision.decision.status === 'completed' ? 'completed' : 'pending',
      completedAt: decision.outcome?.measuredAt },
  ];

  return steps;
}

export default function ApprovalWorkflow({ decision, onStatusChange }: ApprovalWorkflowProps) {
  const [steps] = useState(() => getWorkflowSteps(decision));
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [approvalNotes, setApprovalNotes] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');

  const currentStatus = decision.decision.status;
  const style = STATUS_STYLES[currentStatus];
  const currentStepIndex = steps.findIndex((s) => s.status === 'active');
  const progress = ((steps.filter((s) => s.status === 'completed').length) / steps.length) * 100;

  const handleApprove = () => {
    onStatusChange?.('approved', approvalNotes);
    setShowApproveModal(false);
    setApprovalNotes('');
  };

  const handleReject = () => {
    onStatusChange?.('rejected', rejectionReason);
    setShowRejectModal(false);
    setRejectionReason('');
  };

  return (
    <div className="space-y-4">
      {/* Status Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-bold text-slate-900">Approval Workflow</h3>
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${style.bg} ${style.text} ring-1 ${style.ring}`}>
            {currentStatus}
          </span>
        </div>
        {currentStatus === 'recommended' && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowRejectModal(true)}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-50 text-red-700 hover:bg-red-100 transition-all"
            >
              ✕ Reject
            </button>
            <button
              onClick={() => setShowApproveModal(true)}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition-all"
            >
              ✓ Approve
            </button>
          </div>
        )}
      </div>

      {/* Progress Bar */}
      <div className="glass rounded-xl p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-slate-500">Progress</span>
          <span className="text-xs font-bold text-slate-700">{Math.round(progress)}%</span>
        </div>
        <div className="h-2 rounded-full bg-slate-200 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Workflow Steps */}
      <div className="glass rounded-xl p-4">
        <div className="space-y-1">
          {steps.map((step, index) => {
            const isLast = index === steps.length - 1;
            const isActive = step.status === 'active';
            const isCompleted = step.status === 'completed';
            const isRejected = step.status === 'rejected';

            return (
              <div key={step.id} className="flex items-start gap-3">
                {/* Step indicator */}
                <div className="flex flex-col items-center">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                      isCompleted
                        ? 'bg-emerald-500 text-white'
                        : isActive
                        ? 'bg-blue-500 text-white ring-4 ring-blue-100'
                        : isRejected
                        ? 'bg-red-500 text-white'
                        : 'bg-slate-200 text-slate-500'
                    }`}
                  >
                    {isCompleted ? '✓' : isActive ? (index + 1) : isRejected ? '✕' : (index + 1)}
                  </div>
                  {!isLast && (
                    <div className={`w-0.5 h-8 ${isCompleted ? 'bg-emerald-300' : 'bg-slate-200'}`} />
                  )}
                </div>

                {/* Step content */}
                <div className={`flex-1 pb-4 ${!isLast ? '' : ''}`}>
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-semibold ${isActive ? 'text-blue-700' : isCompleted ? 'text-slate-900' : 'text-slate-500'}`}>
                      {step.label}
                    </span>
                    {isActive && (
                      <span className="px-1.5 py-0.5 text-[9px] font-bold uppercase bg-blue-100 text-blue-600 rounded">
                        Current
                      </span>
                    )}
                  </div>
                  {step.assignee && (
                    <div className="text-xs text-slate-500 mt-0.5">
                      Assigned to: <span className="font-medium">{step.assignee}</span>
                    </div>
                  )}
                  {step.completedAt && (
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      {new Date(step.completedAt).toLocaleString()}
                    </div>
                  )}
                  {step.notes && (
                    <div className="text-xs text-slate-600 mt-1 p-2 rounded-lg bg-white/50 italic">
                      {step.notes}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Decision Info */}
      <div className="glass rounded-xl p-4">
        <h4 className="text-sm font-semibold text-slate-700 mb-2">Decision Details</h4>
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div>
            <span className="text-slate-500">Decided by:</span>
            <span className="ml-2 font-medium text-slate-900">{decision.decision.decidedBy || 'Pending'}</span>
          </div>
          <div>
            <span className="text-slate-500">Decision date:</span>
            <span className="ml-2 font-medium text-slate-900">
              {decision.decision.decidedAt ? new Date(decision.decision.decidedAt).toLocaleDateString() : 'Pending'}
            </span>
          </div>
          {decision.decision.reason && (
            <div className="col-span-2">
              <span className="text-slate-500">Reason:</span>
              <span className="ml-2 font-medium text-slate-900">{decision.decision.reason}</span>
            </div>
          )}
          {decision.decision.overrideNotes && (
            <div className="col-span-2 p-2 rounded-lg bg-amber-50 text-amber-700">
              <span className="font-semibold">Override notes:</span> {decision.decision.overrideNotes}
            </div>
          )}
        </div>
      </div>

      {/* Approve Modal */}
      {showApproveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={() => setShowApproveModal(false)}>
          <div className="glass rounded-2xl p-6 w-full max-w-md animate-glass-in" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-slate-900 mb-4">Approve Recommendation</h3>
            <p className="text-sm text-slate-600 mb-4">
              Approving: <strong>{decision.recommendation.title}</strong>
            </p>
            <textarea
              value={approvalNotes}
              onChange={(e) => setApprovalNotes(e.target.value)}
              placeholder="Add approval notes (optional)"
              className="w-full px-3 py-2 text-sm rounded-xl border border-white/60 bg-white/40 backdrop-blur-md focus:outline-none focus:ring-2 focus:ring-emerald-500/30 h-24 resize-none"
            />
            <div className="flex items-center justify-end gap-3 mt-4">
              <button
                onClick={() => setShowApproveModal(false)}
                className="px-4 py-2 text-sm font-medium rounded-xl text-slate-600 hover:bg-white/60 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleApprove}
                className="px-4 py-2 text-sm font-semibold rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 transition-all"
              >
                ✓ Approve
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={() => setShowRejectModal(false)}>
          <div className="glass rounded-2xl p-6 w-full max-w-md animate-glass-in" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-slate-900 mb-4">Reject Recommendation</h3>
            <p className="text-sm text-slate-600 mb-4">
              Rejecting: <strong>{decision.recommendation.title}</strong>
            </p>
            <textarea
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="Reason for rejection (required)"
              className="w-full px-3 py-2 text-sm rounded-xl border border-white/60 bg-white/40 backdrop-blur-md focus:outline-none focus:ring-2 focus:ring-red-500/30 h-24 resize-none"
            />
            <div className="flex items-center justify-end gap-3 mt-4">
              <button
                onClick={() => setShowRejectModal(false)}
                className="px-4 py-2 text-sm font-medium rounded-xl text-slate-600 hover:bg-white/60 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                disabled={!rejectionReason}
                className="px-4 py-2 text-sm font-semibold rounded-xl bg-red-600 text-white hover:bg-red-700 transition-all disabled:opacity-50"
              >
                ✕ Reject
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
