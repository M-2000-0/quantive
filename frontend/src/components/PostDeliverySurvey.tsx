import { useState } from 'react';

interface SurveyProps {
  orderId?: string;
  productName?: string;
  onSubmit?: (data: SurveyData) => void;
}

interface SurveyData {
  satisfaction: number;
  metExpectations: 'yes' | 'mostly' | 'no';
  wouldRecommend: boolean;
  returnReason?: string;
  comment: string;
}

const EXPECTATION_OPTIONS = [
  { value: 'yes' as const, label: 'Yes, exactly', emoji: '😊', color: 'bg-emerald-50 border-emerald-200 hover:bg-emerald-100' },
  { value: 'mostly' as const, label: 'Mostly', emoji: '😐', color: 'bg-amber-50 border-amber-200 hover:bg-amber-100' },
  { value: 'no' as const, label: 'Not really', emoji: '😞', color: 'bg-red-50 border-red-200 hover:bg-red-100' },
];

const RETURN_REASONS = [
  'Size/Fit issue',
  'Quality not as expected',
  'Didn\'t match description',
  'Found better price',
  'Changed my mind',
  'Damaged on arrival',
  'Other',
];

export default function PostDeliverySurvey({ orderId = 'demo-order', productName = 'your recent purchase', onSubmit }: SurveyProps) {
  const [step, setStep] = useState(0);
  const [data, setData] = useState<SurveyData>({
    satisfaction: 0,
    metExpectations: 'yes',
    wouldRecommend: true,
    comment: '' });
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = () => {
    setSubmitted(true);
    onSubmit?.(data);
  };

  if (submitted) {
    return (
      <div className="glass p-8 text-center max-w-md mx-auto">
        <div className="text-4xl mb-3">🙏</div>
        <h3 className="text-lg font-bold text-slate-900">Thank you for your feedback!</h3>
        <p className="text-sm text-slate-500 mt-2">Your input helps us improve {productName} for future customers.</p>
      </div>
    );
  }

  return (
    <div className="glass p-6 max-w-lg mx-auto">
      {/* Progress */}
      <div className="flex items-center gap-2 mb-6">
        {[0, 1, 2].map(s => (
          <div key={s} className={`flex-1 h-1.5 rounded-full transition-all ${s <= step ? 'bg-blue-500' : 'bg-white/40'}`} />
        ))}
      </div>

      {step === 0 && (
        <div className="space-y-4 animate-glass-in">
          <div>
            <h3 className="text-lg font-bold text-slate-900">How was your experience?</h3>
            <p className="text-sm text-slate-500 mt-1">Rate your satisfaction with {productName}</p>
          </div>
          <div className="flex justify-center gap-3 py-4">
            {[1, 2, 3, 4, 5].map(n => (
              <button
                key={n}
                onClick={() => setData(d => ({ ...d, satisfaction: n }))}
                className={`w-14 h-14 rounded-2xl text-2xl font-bold transition-all ${
                  data.satisfaction === n
                    ? 'bg-blue-500 text-white scale-110 shadow-lg shadow-blue-500/20'
                    : 'bg-white/60 text-slate-400 hover:bg-white/80 hover:text-slate-600 border border-white/40'
                }`}
              >
                {n}
              </button>
            ))}
          </div>
          <div className="flex justify-between text-[11px] text-slate-400 px-2">
            <span>Very dissatisfied</span>
            <span>Very satisfied</span>
          </div>
          <button
            onClick={() => setStep(1)}
            disabled={data.satisfaction === 0}
            className="glass-btn-primary w-full mt-4 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}

      {step === 1 && (
        <div className="space-y-4 animate-glass-in">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Did it meet your expectations?</h3>
            <p className="text-sm text-slate-500 mt-1">How well did the product match what you expected?</p>
          </div>
          <div className="grid grid-cols-3 gap-3 py-2">
            {EXPECTATION_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => setData(d => ({ ...d, metExpectations: opt.value }))}
                className={`p-4 rounded-2xl border-2 text-center transition-all ${
                  data.metExpectations === opt.value
                    ? `${opt.color} border-current scale-105 shadow-md`
                    : 'bg-white/40 border-white/40 hover:bg-white/60'
                }`}
              >
                <div className="text-3xl mb-2">{opt.emoji}</div>
                <div className="text-sm font-medium text-slate-700">{opt.label}</div>
              </button>
            ))}
          </div>

          {data.metExpectations === 'no' && (
            <div className="space-y-2 animate-glass-in">
              <label className="text-sm font-medium text-slate-700">What was the main issue?</label>
              <select
                className="glass-input w-full"
                value={data.returnReason || ''}
                onChange={e => setData(d => ({ ...d, returnReason: e.target.value }))}
              >
                <option value="">Select a reason...</option>
                {RETURN_REASONS.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
          )}

          <div className="flex gap-3 mt-4">
            <button onClick={() => setStep(0)} className="glass-btn flex-1">Back</button>
            <button onClick={() => setStep(2)} className="glass-btn-primary flex-1">Next</button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-4 animate-glass-in">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Would you recommend us?</h3>
            <p className="text-sm text-slate-500 mt-1">Your honest feedback helps us improve</p>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => setData(d => ({ ...d, wouldRecommend: true }))}
              className={`flex-1 p-4 rounded-2xl border-2 text-center transition-all ${
                data.wouldRecommend
                  ? 'bg-emerald-50 border-emerald-300 text-emerald-700 scale-105'
                  : 'bg-white/40 border-white/40 hover:bg-white/60'
              }`}
            >
              <div className="text-2xl mb-1">👍</div>
              <div className="text-sm font-medium">Yes</div>
            </button>
            <button
              onClick={() => setData(d => ({ ...d, wouldRecommend: false }))}
              className={`flex-1 p-4 rounded-2xl border-2 text-center transition-all ${
                !data.wouldRecommend
                  ? 'bg-red-50 border-red-300 text-red-700 scale-105'
                  : 'bg-white/40 border-white/40 hover:bg-white/60'
              }`}
            >
              <div className="text-2xl mb-1">👎</div>
              <div className="text-sm font-medium">No</div>
            </button>
          </div>

          <div>
            <label className="text-sm font-medium text-slate-700 mb-1 block">Any additional comments? (optional)</label>
            <textarea
              className="glass-input w-full h-24 resize-none"
              placeholder="Tell us more about your experience..."
              value={data.comment}
              onChange={e => setData(d => ({ ...d, comment: e.target.value }))}
            />
          </div>

          <div className="flex gap-3 mt-4">
            <button onClick={() => setStep(1)} className="glass-btn flex-1">Back</button>
            <button onClick={handleSubmit} className="glass-btn-primary flex-1">Submit Feedback</button>
          </div>
        </div>
      )}
    </div>
  );
}
