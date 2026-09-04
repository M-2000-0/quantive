import { useState, useEffect } from 'react';
import { useAuth } from '../stores/auth';
import { DISCLAIMER_ACCEPTANCE_KEY, DISCLAIMER_VERSION, DISCLAIMER_ACCEPTANCE_DATE_KEY } from '../lib/legalContent';
import { TriangleAlert as AlertTriangle } from 'lucide-react';

interface DisclaimerBannerProps {
 onAccept?: () => void;
}

export function useDisclaimerAccepted(): boolean {
 const { user } = useAuth();
 const [accepted, setAccepted] = useState(false);

 useEffect(() => {
 if (!user) {
 setAccepted(false);
 return;
 }

 const key = `${DISCLAIMER_ACCEPTANCE_KEY}_${user.id || user.email}`;
 const versionKey = `${key}_version`;
 const storedVersion = localStorage.getItem(versionKey);
 const stored = localStorage.getItem(key);

 // Re-accept if version changed
 if (stored === 'true' && storedVersion === DISCLAIMER_VERSION) {
 setAccepted(true);
 } else {
 setAccepted(false);
 }
 }, [user]);

 const accept = () => {
 const key = `${DISCLAIMER_ACCEPTANCE_KEY}_${user?.id || user?.email}`;
 localStorage.setItem(key, 'true');
 localStorage.setItem(`${key}_version`, DISCLAIMER_VERSION);
 localStorage.setItem(DISCLAIMER_ACCEPTANCE_DATE_KEY, new Date().toISOString());
 setAccepted(true);
 };

 return accepted;
}

export default function DisclaimerBanner({ onAccept }: DisclaimerBannerProps) {
 const [expanded, setExpanded] = useState(false);
 const [acknowledged, setAcknowledged] = useState(false);
 const { user } = useAuth();

 const handleAccept = () => {
 if (!acknowledged) return;
 const key = `${DISCLAIMER_ACCEPTANCE_KEY}_${user?.id || user?.email}`;
 localStorage.setItem(key, 'true');
 localStorage.setItem(`${key}_version`, DISCLAIMER_VERSION);
 localStorage.setItem(DISCLAIMER_ACCEPTANCE_DATE_KEY, new Date().toISOString());
 onAccept?.();
 };

 return (
 <div className="fixed inset-0 z-[10000] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
 <div className="relative w-full max-w-2xl max-h-[85vh] overflow-y-auto bg-white rounded-2xl shadow-2xl border border-slate-200">
 {/* Header */}
 <div className="sticky top-0 bg-white border-b border-slate-200 px-6 py-4 rounded-t-2xl z-10">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center">
 <AlertTriangle className="w-5 h-5" />
 </div>
 <div>
 <h2 className="text-lg font-bold text-slate-900">Financial Disclaimer</h2>
 <p className="text-xs text-slate-500">Please read and acknowledge before proceeding</p>
 </div>
 </div>
 </div>

 {/* Content */}
 <div className="px-6 py-5 space-y-4">
 {/* Key warnings */}
 <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
 <h3 className="text-sm font-bold text-amber-800 mb-2"> <AlertTriangle className="w-4 h-4 inline" /> Important Warnings</h3>
 <ul className="space-y-2 text-sm text-amber-900">
 <li className="flex items-start gap-2">
 <span className="text-amber-500 mt-0.5">•</span>
 <span><strong>Not Financial Advice:</strong> Quantive is a decision-support tool, not a financial advisor. Nothing here constitutes investment, legal, or tax advice.</span>
 </li>
 <li className="flex items-start gap-2">
 <span className="text-amber-500 mt-0.5">•</span>
 <span><strong>No Guarantees:</strong> Optimization results do not guarantee any specific financial outcome. All investments carry risk of loss.</span>
 </li>
 <li className="flex items-start gap-2">
 <span className="text-amber-500 mt-0.5">•</span>
 <span><strong>Your Responsibility:</strong> You are solely responsible for evaluating strategies and making investment decisions. Consult qualified professionals.</span>
 </li>
 <li className="flex items-start gap-2">
 <span className="text-amber-500 mt-0.5">•</span>
 <span><strong>Model Limitations:</strong> Algorithms may not account for all market factors. Past performance does not predict future results.</span>
 </li>
 </ul>
 </div>

 {/* Expanded terms */}
 <div>
 <button
 onClick={() => setExpanded(!expanded)}
 className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
 >
 {expanded ? '▼' : '▶'} Read full Terms of Service & Privacy Policy
 </button>
 {expanded && (
 <div className="mt-3 p-4 bg-slate-50 rounded-xl text-xs text-slate-600 max-h-60 overflow-y-auto space-y-4 border border-slate-200">
 <div>
 <h4 className="font-bold text-slate-800 mb-1">Limitation of Liability</h4>
 <p>To the maximum extent permitted by law, Quantive shall not be liable for any indirect, incidental, special, consequential, or punitive damages, including loss of profits, data, or business opportunity. Total liability is limited to the amount paid in the preceding 12 months.</p>
 </div>
 <div>
 <h4 className="font-bold text-slate-800 mb-1">Indemnification</h4>
 <p>You agree to indemnify and hold harmless Quantive from any claims arising from your use of the Platform, violation of these Terms, or violation of applicable law.</p>
 </div>
 <div>
 <h4 className="font-bold text-slate-800 mb-1">Data & Privacy</h4>
 <p>We collect and process data as described in our Privacy Policy. Portfolio data is encrypted at rest. We do not sell your personal information. See the full Privacy Policy for details.</p>
 </div>
 <div>
 <h4 className="font-bold text-slate-800 mb-1">Regulatory Notice</h4>
 <p>If you are regulated by the SEC, FCA, FINRA, or equivalent, platform outputs do not constitute "investment advice" under applicable regulations. You remain responsible for regulatory compliance.</p>
 </div>
 </div>
 )}
 </div>

 {/* Acknowledgment checkbox */}
 <label className="flex items-start gap-3 p-4 bg-slate-50 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-100 transition-colors">
 <input
 type="checkbox"
 checked={acknowledged}
 onChange={(e) => setAcknowledged(e.target.checked)}
 className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
 />
 <span className="text-sm text-slate-700">
 I have read and understood the financial disclaimer. I understand that Quantive is a decision-support tool only,
 that no guarantees are made about outcomes, and that I am solely responsible for my investment decisions.
 </span>
 </label>
 </div>

 {/* Footer */}
 <div className="sticky bottom-0 bg-white border-t border-slate-200 px-6 py-4 rounded-b-2xl">
 <div className="flex items-center justify-between">
 <p className="text-[10px] text-slate-400">Version {DISCLAIMER_VERSION} • Last updated August 2026</p>
 <div className="flex gap-3">
 <a
 href="/legal/terms"
 target="_blank"
 className="text-xs text-slate-500 hover:text-slate-700 underline"
 >
 Terms
 </a>
 <a
 href="/legal/privacy"
 target="_blank"
 className="text-xs text-slate-500 hover:text-slate-700 underline"
 >
 Privacy
 </a>
 <a
 href="/legal/disclaimer"
 target="_blank"
 className="text-xs text-slate-500 hover:text-slate-700 underline"
 >
 Full Disclaimer
 </a>
 <button
 onClick={handleAccept}
 disabled={!acknowledged}
 className={`px-5 py-2 rounded-xl text-sm font-semibold transition-all ${
 acknowledged
 ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm'
 : 'bg-slate-200 text-slate-400 cursor-not-allowed'
 }`}
 >
 I Understand — Continue
 </button>
 </div>
 </div>
 </div>
 </div>
 </div>
 );
}
