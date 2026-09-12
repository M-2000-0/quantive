import React, { useState } from 'react';
import { CircleCheck as CheckCircle, CircleX as XCircle } from 'lucide-react';

interface ApprovalStep {
 id: string;
 role: string;
 title: string;
 signer: string;
 status: 'pending' | 'approved' | 'rejected' | 'escalated' | 'vetoed';
 signedAt?: string;
 comments?: string;
 deadline: string;
 isEscalated: boolean;
 digitalSignature?: string;
}

interface ApprovalWorkflow {
 id: string;
 title: string;
 type: 'optimization' | 'issuance' | 'policy' | 'emergency';
 submittedBy: string;
 submittedAt: string;
 priority: 'critical' | 'high' | 'medium' | 'low';
 status: 'in_progress' | 'approved' | 'rejected' | 'vetoed' | 'expired';
 currentStep: number;
 steps: ApprovalStep[];
 description: string;
 documents: string[];
}

const MOCK_WORKFLOWS: ApprovalWorkflow[] = [
 {
 id: 'aw-001',
 title: 'Refinance $2.4B 2027 Maturity',
 type: 'issuance',
 submittedBy: 'Sarah Chen (Senior Analyst)',
 submittedAt: '2026-08-24T09:00:00Z',
 priority: 'critical',
 status: 'in_progress',
 currentStep: 2,
 description: 'Proposed refinancing of $2.4B maturing in 2027 via 10Y bond issuance at estimated 4.1% yield. Reduces refinancing risk by 34% and extends average maturity by 2.3 years.',
 documents: ['Bond_Pricing_Model.xlsx', 'Risk_Analysis.pdf', 'Market_Assessment.pdf'],
 steps: [
 { id: 's1', role: 'analyst', title: 'Analyst Review', signer: 'Sarah Chen', status: 'approved', signedAt: '2026-08-24T09:15:00Z', comments: 'Recommendation: Proceed. Market conditions favorable.', deadline: '2026-08-24T17:00:00Z', isEscalated: false, digitalSignature: 'SC-2026-A4F2' },
 { id: 's2', role: 'senior_analyst', title: 'Senior Analyst Approval', signer: 'James Morrison', status: 'approved', signedAt: '2026-08-24T11:30:00Z', comments: 'Concur with analyst recommendation. Yield spread acceptable.', deadline: '2026-08-25T12:00:00Z', isEscalated: false, digitalSignature: 'JM-2026-B7E1' },
 { id: 's3', role: 'director', title: 'Director Approval', signer: 'Dr. Amara Okafor', status: 'pending', deadline: '2026-08-26T12:00:00Z', isEscalated: false },
 { id: 's4', role: 'treasury', title: 'Treasury Approval', signer: 'Minister of Finance', status: 'pending', deadline: '2026-08-27T12:00:00Z', isEscalated: false },
 { id: 's5', role: 'minister', title: 'Minister Approval', signer: 'Hon. Minister', status: 'pending', deadline: '2026-08-28T17:00:00Z', isEscalated: false },
 ] },
 {
 id: 'aw-002',
 title: 'Emergency Liquidity Injection',
 type: 'emergency',
 submittedBy: 'Emergency Operations Center',
 submittedAt: '2026-08-23T02:00:00Z',
 priority: 'critical',
 status: 'in_progress',
 currentStep: 3,
 description: 'Emergency $800M short-term issuance to address liquidity gap caused by unexpected outflows. Requires expedited approval.',
 documents: ['Emergency_Assessment.pdf', 'Liquidity_Forecast.xlsx'],
 steps: [
 { id: 's1', role: 'analyst', title: 'Analyst Review', signer: 'Emergency Duty Officer', status: 'approved', signedAt: '2026-08-23T02:15:00Z', comments: 'Critical: Liquidity buffer falls below 15% threshold.', deadline: '2026-08-23T03:00:00Z', isEscalated: true, digitalSignature: 'EO-2026-C9D3' },
 { id: 's2', role: 'senior_analyst', title: 'Senior Analyst Approval', signer: 'Night Shift Director', status: 'approved', signedAt: '2026-08-23T02:30:00Z', comments: 'Emergency protocol activated. Recommending expedited chain.', deadline: '2026-08-23T04:00:00Z', isEscalated: true, digitalSignature: 'ND-2026-D1F5' },
 { id: 's3', role: 'director', title: 'Director Approval', signer: 'Dr. Amara Okafor', status: 'approved', signedAt: '2026-08-23T06:00:00Z', comments: 'Approved under emergency provisions. Minister notified.', deadline: '2026-08-23T08:00:00Z', isEscalated: true, digitalSignature: 'AO-2026-E2G7' },
 { id: 's4', role: 'treasury', title: 'Treasury Approval', signer: 'Minister of Finance', status: 'pending', deadline: '2026-08-23T12:00:00Z', isEscalated: true },
 { id: 's5', role: 'minister', title: 'Minister Approval', signer: 'Hon. Minister', status: 'pending', deadline: '2026-08-23T18:00:00Z', isEscalated: true },
 ] },
 {
 id: 'aw-003',
 title: 'Green Bond Framework Update',
 type: 'policy',
 submittedBy: 'ESG Committee',
 submittedAt: '2026-08-20T10:00:00Z',
 priority: 'medium',
 status: 'approved',
 currentStep: 5,
 description: 'Update Green Bond Framework to align with ICMA 2026 Green Bond Principles. Includes new eligibility criteria for renewable energy projects.',
 documents: ['Framework_Draft.docx', 'ICMA_Compliance.xlsx', 'Stakeholder_Feedback.pdf'],
 steps: [
 { id: 's1', role: 'analyst', title: 'Analyst Review', signer: 'ESG Analyst', status: 'approved', signedAt: '2026-08-20T14:00:00Z', comments: 'Framework meets all ICMA requirements.', deadline: '2026-08-21T17:00:00Z', isEscalated: false, digitalSignature: 'EA-2026-F3H9' },
 { id: 's2', role: 'senior_analyst', title: 'Senior Analyst Approval', signer: 'Head of ESG', status: 'approved', signedAt: '2026-08-21T10:00:00Z', comments: 'Excellent work. Minor formatting suggestions implemented.', deadline: '2026-08-22T12:00:00Z', isEscalated: false, digitalSignature: 'HE-2026-G4I1' },
 { id: 's3', role: 'director', title: 'Director Approval', signer: 'Dr. Amara Okafor', status: 'approved', signedAt: '2026-08-22T15:00:00Z', comments: 'Approved. Forward to Treasury.', deadline: '2026-08-23T12:00:00Z', isEscalated: false, digitalSignature: 'AO-2026-H5J3' },
 { id: 's4', role: 'treasury', title: 'Treasury Approval', signer: 'Deputy Minister', status: 'approved', signedAt: '2026-08-23T09:00:00Z', comments: 'Framework approved for publication.', deadline: '2026-08-24T12:00:00Z', isEscalated: false, digitalSignature: 'DM-2026-I6K5' },
 { id: 's5', role: 'minister', title: 'Minister Approval', signer: 'Hon. Minister', status: 'approved', signedAt: '2026-08-24T11:00:00Z', comments: 'Approved. Publish immediately.', deadline: '2026-08-25T17:00:00Z', isEscalated: false, digitalSignature: 'HM-2026-J7L7' },
 ] },
];

const ROLE_COLORS: Record<string, string> = {
 analyst: 'bg-blue-500/20 text-blue-400',
 senior_analyst: 'bg-purple-500/20 text-purple-400',
 director: 'bg-amber-500/20 text-amber-400',
 treasury: 'bg-green-500/20 text-green-400',
 minister: 'bg-red-500/20 text-red-400' };

const STATUS_ICONS: Record<string, string> = {
 approved: 'CheckCircle',
 rejected: 'XCircle',
 pending: '⏳',
 escalated: '🚨',
 vetoed: '🛑',
 in_progress: 'RefreshCw',
 expired: 'Clock' };

export default function ApprovalWorkflowSystem() {
 const [workflows, setWorkflows] = useState<ApprovalWorkflow[]>(MOCK_WORKFLOWS);
 const [selectedWorkflow, setSelectedWorkflow] = useState<ApprovalWorkflow | null>(null);
 const [activeTab, setActiveTab] = useState<'pending' | 'completed' | 'all'>('pending');
 const [showApprovalModal, setShowApprovalModal] = useState(false);
 const [approvalComment, setApprovalComment] = useState('');

 const filteredWorkflows = workflows.filter(w => {
 if (activeTab === 'pending') return w.status === 'in_progress';
 if (activeTab === 'completed') return w.status === 'approved' || w.status === 'rejected' || w.status === 'vetoed';
 return true;
 });

 const handleApprove = (workflowId: string, stepId: string) => {
 setWorkflows(prev => prev.map(w => {
 if (w.id !== workflowId) return w;
 return {
 ...w,
 steps: w.steps.map(s => {
 if (s.id !== stepId) return s;
 return {
 ...s,
 status: 'approved' as const,
 signedAt: new Date().toISOString(),
 comments: approvalComment,
 digitalSignature: `AUTO-${Date.now().toString(36).toUpperCase()}` };
 }),
 currentStep: w.currentStep + 1,
 status: w.currentStep + 1 >= w.steps.length ? 'approved' : 'in_progress' };
 }));
 setShowApprovalModal(false);
 setApprovalComment('');
 };

 const handleReject = (workflowId: string, stepId: string) => {
 setWorkflows(prev => prev.map(w => {
 if (w.id !== workflowId) return w;
 return {
 ...w,
 steps: w.steps.map(s => {
 if (s.id !== stepId) return s;
 return { ...s, status: 'rejected' as const, signedAt: new Date().toISOString(), comments: approvalComment };
 }),
 status: 'rejected' };
 }));
 setShowApprovalModal(false);
 setApprovalComment('');
 };

 const handleVeto = (workflowId: string, stepId: string) => {
 setWorkflows(prev => prev.map(w => {
 if (w.id !== workflowId) return w;
 return {
 ...w,
 steps: w.steps.map(s => {
 if (s.id !== stepId) return s;
 return { ...s, status: 'vetoed' as const, signedAt: new Date().toISOString(), comments: `VETO: ${approvalComment}` };
 }),
 status: 'vetoed' };
 }));
 setShowApprovalModal(false);
 setApprovalComment('');
 };

 const handleEscalate = (workflowId: string, stepId: string) => {
 setWorkflows(prev => prev.map(w => {
 if (w.id !== workflowId) return w;
 return {
 ...w,
 steps: w.steps.map(s => {
 if (s.id !== stepId) return s;
 return { ...s, isEscalated: true, status: 'escalated' as const };
 }) };
 }));
 };

 const pendingCount = workflows.filter(w => w.status === 'in_progress').length;
 const criticalCount = workflows.filter(w => w.priority === 'critical' && w.status === 'in_progress').length;

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center">
 <span className="text-lg">✍️</span>
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Cabinet Approval Workflow</h2>
 <p className="text-sm text-slate-400">Multi-level government approval chains with digital signatures</p>
 </div>
 </div>
 <div className="flex gap-3">
 <div className="glass px-4 py-2 rounded-xl text-center">
 <p className="text-2xl font-bold text-amber-400">{pendingCount}</p>
 <p className="text-xs text-slate-400">Pending</p>
 </div>
 <div className="glass px-4 py-2 rounded-xl text-center">
 <p className="text-2xl font-bold text-red-400">{criticalCount}</p>
 <p className="text-xs text-slate-400">Critical</p>
 </div>
 </div>
 </div>

 {/* Tabs */}
 <div className="flex gap-2">
 {(['pending', 'completed', 'all'] as const).map(tab => (
 <button
 key={tab}
 onClick={() => setActiveTab(tab)}
 className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
 activeTab === tab
 ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
 : 'bg-white/5 text-slate-400 hover:bg-white/10 border border-transparent'
 }`}
 >
 {tab.charAt(0).toUpperCase() + tab.slice(1)} ({tab === 'pending' ? pendingCount : tab === 'completed' ? workflows.length - pendingCount : workflows.length})
 </button>
 ))}
 </div>

 <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
 {/* Workflow List */}
 <div className="space-y-3">
 {filteredWorkflows.map(w => (
 <button
 key={w.id}
 onClick={() => setSelectedWorkflow(w)}
 className={`w-full text-left glass rounded-xl p-4 transition-all ${
 selectedWorkflow?.id === w.id ? 'ring-2 ring-indigo-500/50' : 'hover:bg-white/5'
 }`}
 >
 <div className="flex items-start justify-between mb-2">
 <div className="flex items-center gap-2">
 <span className={`px-2 py-0.5 rounded text-xs font-medium ${
 w.priority === 'critical' ? 'bg-red-500/20 text-red-400' :
 w.priority === 'high' ? 'bg-amber-500/20 text-amber-400' :
 'bg-slate-500/20 text-slate-400'
 }`}>
 {w.priority.toUpperCase()}
 </span>
 <span className="text-xs text-slate-500 capitalize">{w.type}</span>
 </div>
 <span className="text-lg">{STATUS_ICONS[w.status]}</span>
 </div>
 <h4 className="text-white text-sm font-medium mb-1">{w.title}</h4>
 <p className="text-xs text-slate-400 mb-2">By {w.submittedBy}</p>
 
 {/* Progress bar */}
 <div className="flex items-center gap-2">
 <div className="flex-1 bg-white/5 rounded-full h-1.5">
 <div
 className="h-1.5 rounded-full bg-indigo-400"
 style={{ width: `${(w.steps.filter(s => s.status === 'approved').length / w.steps.length) * 100}%` }}
 />
 </div>
 <span className="text-xs text-slate-500">
 {w.steps.filter(s => s.status === 'approved').length}/{w.steps.length}
 </span>
 </div>
 </button>
 ))}
 </div>

 {/* Detail Panel */}
 <div className="lg:col-span-2">
 {selectedWorkflow ? (
 <div className="glass rounded-2xl p-6 space-y-6">
 <div className="flex items-start justify-between">
 <div>
 <h3 className="text-lg font-bold text-white">{selectedWorkflow.title}</h3>
 <p className="text-sm text-slate-400 mt-1">{selectedWorkflow.description}</p>
 </div>
 <span className={`px-3 py-1 rounded-lg text-xs font-medium ${
 selectedWorkflow.status === 'approved' ? 'bg-green-500/20 text-green-400' :
 selectedWorkflow.status === 'rejected' ? 'bg-red-500/20 text-red-400' :
 selectedWorkflow.status === 'vetoed' ? 'bg-red-500/20 text-red-400' :
 'bg-amber-500/20 text-amber-400'
 }`}>
 {STATUS_ICONS[selectedWorkflow.status]} {selectedWorkflow.status.replace('_', ' ').toUpperCase()}
 </span>
 </div>

 {/* Documents */}
 <div>
 <h4 className="text-xs font-medium text-slate-500 mb-2">ATTACHED DOCUMENTS</h4>
 <div className="flex gap-2 flex-wrap">
 {selectedWorkflow.documents.map((doc, i) => (
 <span key={i} className="px-3 py-1.5 bg-white/5 rounded-lg text-xs text-slate-300 flex items-center gap-1">
 📄 {doc}
 </span>
 ))}
 </div>
 </div>

 {/* Approval Chain */}
 <div>
 <h4 className="text-xs font-medium text-slate-500 mb-4">APPROVAL CHAIN</h4>
 <div className="space-y-3">
 {selectedWorkflow.steps.map((step, i) => (
 <div key={step.id} className={`relative flex items-start gap-4 p-4 rounded-xl border ${
 step.status === 'approved' ? 'bg-green-500/5 border-green-500/20' :
 step.status === 'rejected' || step.status === 'vetoed' ? 'bg-red-500/5 border-red-500/20' :
 step.status === 'escalated' ? 'bg-amber-500/5 border-amber-500/20' :
 i === selectedWorkflow.currentStep ? 'bg-indigo-500/5 border-indigo-500/20' :
 'bg-white/5 border-white/10'
 }`}>
 {/* Connector line */}
 {i < selectedWorkflow.steps.length - 1 && (
 <div className="absolute left-8 top-14 w-0.5 h-6 bg-white/10" />
 )}
 
 {/* Step number */}
 <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
 step.status === 'approved' ? 'bg-green-500/20 text-green-400' :
 step.status === 'rejected' || step.status === 'vetoed' ? 'bg-red-500/20 text-red-400' :
 step.status === 'escalated' ? 'bg-amber-500/20 text-amber-400' :
 i === selectedWorkflow.currentStep ? 'bg-indigo-500/20 text-indigo-400' :
 'bg-white/10 text-slate-500'
 }`}>
 {i + 1}
 </div>

 <div className="flex-1 min-w-0">
 <div className="flex items-center gap-2 mb-1">
 <span className={`px-2 py-0.5 rounded text-xs ${ROLE_COLORS[step.role]}`}>
 {step.title}
 </span>
 {step.isEscalated && (
 <span className="px-2 py-0.5 bg-amber-500/20 text-amber-400 rounded text-xs">
 🚨 ESCALATED
 </span>
 )}
 </div>
 <p className="text-white text-sm font-medium">{step.signer}</p>
 
 {step.status === 'approved' && step.signedAt && (
 <div className="mt-2 bg-white/5 rounded-lg p-2">
 <p className="text-xs text-green-400"> <CheckCircle className="w-4 h-4 inline" /> Approved {new Date(step.signedAt).toLocaleString()}</p>
 {step.digitalSignature && (
 <p className="text-xs text-slate-500 font-mono">Sig: {step.digitalSignature}</p>
 )}
 {step.comments && (
 <p className="text-xs text-slate-400 mt-1">"{step.comments}"</p>
 )}
 </div>
 )}

 {step.status === 'pending' && i === selectedWorkflow.currentStep && (
 <div className="mt-2 text-xs text-slate-400">
 Deadline: {new Date(step.deadline).toLocaleString()}
 </div>
 )}

 {/* Action buttons for current step */}
 {step.status === 'pending' && i === selectedWorkflow.currentStep && selectedWorkflow.status === 'in_progress' && (
 <div className="mt-3 flex gap-2">
 <button
 onClick={() => setShowApprovalModal(true)}
 className="px-3 py-1.5 bg-green-500/20 text-green-400 rounded-lg text-xs font-medium hover:bg-green-500/30 transition-colors"
 >
 <CheckCircle className="w-4 h-4 inline" /> Approve
 </button>
 <button
 onClick={() => handleReject(selectedWorkflow.id, step.id)}
 className="px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg text-xs font-medium hover:bg-red-500/30 transition-colors"
 >
 <XCircle className="w-4 h-4 inline" /> Reject
 </button>
 <button
 onClick={() => handleVeto(selectedWorkflow.id, step.id)}
 className="px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg text-xs font-medium hover:bg-red-500/30 transition-colors"
 >
 🛑 Veto
 </button>
 <button
 onClick={() => handleEscalate(selectedWorkflow.id, step.id)}
 className="px-3 py-1.5 bg-amber-500/20 text-amber-400 rounded-lg text-xs font-medium hover:bg-amber-500/30 transition-colors"
 >
 🚨 Escalate
 </button>
 </div>
 )}
 </div>

 {/* Status badge */}
 <div className="text-lg flex-shrink-0">
 {STATUS_ICONS[step.status]}
 </div>
 </div>
 ))}
 </div>
 </div>
 </div>
 ) : (
 <div className="glass rounded-2xl p-12 text-center">
 <div className="text-4xl mb-4">✍️</div>
 <h3 className="text-white font-bold mb-2">Select a Workflow</h3>
 <p className="text-sm text-slate-400">Click a workflow to view its approval chain and take action</p>
 </div>
 )}
 </div>
 </div>

 {/* Approval Modal */}
 {showApprovalModal && selectedWorkflow && (
 <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
 <div className="glass rounded-2xl p-6 w-full max-w-md space-y-4">
 <h3 className="text-lg font-bold text-white">Digital Signature</h3>
 <p className="text-sm text-slate-400">
 You are about to digitally sign as the next approver in the chain.
 </p>
 <div className="bg-white/5 rounded-xl p-4">
 <p className="text-xs text-slate-500 mb-1">Workflow</p>
 <p className="text-sm text-white">{selectedWorkflow.title}</p>
 </div>
 <div>
 <label className="text-xs text-slate-500 block mb-1">Approval Comments</label>
 <textarea
 value={approvalComment}
 onChange={(e) => setApprovalComment(e.target.value)}
 className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-green-500/50 transition-colors text-sm"
 rows={3}
 placeholder="Optional: Add comments for the record..."
 />
 </div>
 <div className="flex gap-3">
 <button
 onClick={() => setShowApprovalModal(false)}
 className="flex-1 py-3 bg-white/5 border border-white/10 rounded-xl text-slate-400 hover:bg-white/10 transition-colors"
 >
 Cancel
 </button>
 <button
 onClick={() => {
 const currentStep = selectedWorkflow.steps[selectedWorkflow.currentStep];
 handleApprove(selectedWorkflow.id, currentStep.id);
 }}
 className="flex-1 py-3 bg-gradient-to-r from-green-500 to-emerald-600 rounded-xl text-white font-medium hover:opacity-90 transition-opacity"
 >
 ✍️ Sign & Approve
 </button>
 </div>
 </div>
 </div>
 )}
 </div>
 );
}
