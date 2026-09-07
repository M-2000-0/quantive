// ── Risk Profile Quiz Component ─────────────────────────────────────
// Interactive 10-question quiz that assesses risk tolerance and
// recommends a conservative/balanced/aggressive portfolio allocation.

import { useState, useMemo } from 'react';
import {
 QUIZ_QUESTIONS,
 assessProfile,
 TARGET_ALLOCATIONS,
 type RiskProfile,
 type ProfileRecommendation } from '../lib/allocationTarget';
import { Target } from 'lucide-react';

interface RiskProfileQuizProps {
 onComplete?: (recommendation: ProfileRecommendation) => void;
 /** Pre-filled answers (for editing existing profile) */
 initialAnswers?: Record<string, number>;
}

export default function RiskProfileQuiz({ onComplete, initialAnswers = {} }: RiskProfileQuizProps) {
 const [answers, setAnswers] = useState<Record<string, number>>(initialAnswers);
 const [currentStep, setCurrentStep] = useState(0);
 const [completed, setCompleted] = useState(false);
 const [recommendation, setRecommendation] = useState<ProfileRecommendation | null>(null);

 const totalQuestions = QUIZ_QUESTIONS.length;
 const answeredCount = Object.keys(answers).length;
 const progress = (answeredCount / totalQuestions) * 100;

 const currentQuestion = QUIZ_QUESTIONS[currentStep];
 const isLastStep = currentStep === totalQuestions - 1;
 const canProceed = answers[currentQuestion?.id] !== undefined;

 const handleAnswer = (questionId: string, value: number) => {
 setAnswers((prev) => ({ ...prev, [questionId]: value }));
 };

 const handleNext = () => {
 if (currentStep < totalQuestions - 1) {
 setCurrentStep(currentStep + 1);
 } else {
 // Complete the quiz
 const result = assessProfile(answers);
 setRecommendation(result);
 setCompleted(true);
 onComplete?.(result);
 }
 };

 const handleBack = () => {
 if (currentStep > 0) {
 setCurrentStep(currentStep - 1);
 }
 };

 const handleRestart = () => {
 setAnswers({});
 setCurrentStep(0);
 setCompleted(false);
 setRecommendation(null);
 };

 const profileColor = (profile: RiskProfile) => {
 switch (profile) {
 case 'conservative': return 'from-blue-500 to-cyan-500';
 case 'balanced': return 'from-emerald-500 to-teal-500';
 case 'aggressive': return 'from-orange-500 to-red-500';
 }
 };

 const profileBg = (profile: RiskProfile) => {
 switch (profile) {
 case 'conservative': return 'bg-blue-50 border-blue-200 text-blue-800';
 case 'balanced': return 'bg-emerald-50 border-emerald-200 text-emerald-800';
 case 'aggressive': return 'bg-orange-50 border-orange-200 text-orange-800';
 }
 };

 // ── Quiz Questions View ──────────────────────────────────────────

 if (!completed && currentQuestion) {
 return (
 <div className="glass rounded-2xl p-6 animate-glass-in">
 {/* Header */}
 <div className="flex items-center justify-between mb-6">
 <div>
 <h3 className="text-lg font-bold text-slate-900"> <Target className="w-4 h-4 inline" /> Risk Profile Assessment</h3>
 <p className="text-sm text-slate-500 mt-1">
 Answer {totalQuestions} questions to find your ideal portfolio allocation
 </p>
 </div>
 <span className="text-sm font-bold text-slate-400">
 {currentStep + 1}/{totalQuestions}
 </span>
 </div>

 {/* Progress Bar */}
 <div className="h-2 rounded-full bg-slate-200 mb-6 overflow-hidden">
 <div
 className="h-full rounded-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500"
 style={{ width: `${progress}%` }}
 />
 </div>

 {/* Category Badge */}
 <div className="mb-4">
 <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-slate-100 text-slate-600">
 {currentQuestion.category.replace('_', ' ')}
 </span>
 </div>

 {/* Question */}
 <h4 className="text-base font-semibold text-slate-900 mb-4">
 {currentQuestion.question}
 </h4>

 {/* Options */}
 <div className="space-y-2 mb-6">
 {currentQuestion.options.map((option) => {
 const isSelected = answers[currentQuestion.id] === option.value;
 return (
 <button
 key={option.value}
 onClick={() => handleAnswer(currentQuestion.id, option.value)}
 className={`w-full text-left p-3 rounded-xl border transition-all ${
 isSelected
 ? 'border-blue-400 bg-blue-50/80 ring-2 ring-blue-500/20'
 : 'border-white/40 bg-white/30 hover:border-slate-200 hover:bg-white/50'
 }`}
 >
 <div className="flex items-center gap-3">
 <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
 isSelected ? 'border-blue-500 bg-blue-500' : 'border-slate-300'
 }`}>
 {isSelected && (
 <div className="w-2 h-2 rounded-full bg-white" />
 )}
 </div>
 <div>
 <span className={`text-sm font-medium ${isSelected ? 'text-blue-900' : 'text-slate-900'}`}>
 {option.label}
 </span>
 {option.description && (
 <span className="block text-xs text-slate-500 mt-0.5">
 {option.description}
 </span>
 )}
 </div>
 </div>
 </button>
 );
 })}
 </div>

 {/* Navigation */}
 <div className="flex items-center justify-between">
 <button
 onClick={handleBack}
 disabled={currentStep === 0}
 className="px-4 py-2 text-sm font-medium rounded-xl transition-all disabled:opacity-30 disabled:cursor-not-allowed text-slate-600 hover:bg-white/50"
 >
 ← Back
 </button>
 <button
 onClick={handleNext}
 disabled={!canProceed}
 className={`px-6 py-2 text-sm font-semibold rounded-xl transition-all disabled:opacity-30 disabled:cursor-not-allowed ${
 isLastStep
 ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-md hover:shadow-lg'
 : 'bg-blue-600 text-white hover:bg-blue-700'
 }`}
 >
 {isLastStep ? 'Get My Profile →' : 'Next →'}
 </button>
 </div>
 </div>
 );
 }

 // ── Results View ─────────────────────────────────────────────────

 if (completed && recommendation) {
 const target = recommendation.targetAllocation;

 return (
 <div className="glass rounded-2xl p-6 animate-glass-in">
 {/* Header */}
 <div className="text-center mb-6">
 <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r ${profileColor(recommendation.profile)} text-white font-bold text-sm mb-3`}>
 {recommendation.profile === 'conservative' ? 'Shield' : recommendation.profile === 'balanced' ? 'Scale' : 'Rocket'}
 {target.label} Profile
 </div>
 <h3 className="text-xl font-bold text-slate-900">Your Recommended Allocation</h3>
 <p className="text-sm text-slate-500 mt-1">
 Based on your answers, we recommend a {target.label.toLowerCase()} approach
 </p>
 </div>

 {/* Confidence & Key Metrics */}
 <div className="grid grid-cols-3 gap-3 mb-6">
 <div className="p-3 rounded-xl bg-blue-50/50 border border-blue-200/50 text-center">
 <div className="text-2xl font-bold text-blue-600">{recommendation.confidence}%</div>
 <div className="text-[10px] font-medium text-blue-700 uppercase">Confidence</div>
 </div>
 <div className="p-3 rounded-xl bg-emerald-50/50 border border-emerald-200/50 text-center">
 <div className="text-2xl font-bold text-emerald-600">{recommendation.expectedReturn}</div>
 <div className="text-[10px] font-medium text-emerald-700 uppercase">Expected Return</div>
 </div>
 <div className="p-3 rounded-xl bg-red-50/50 border border-red-200/50 text-center">
 <div className="text-2xl font-bold text-red-600">{recommendation.maxDrawdown}</div>
 <div className="text-[10px] font-medium text-red-700 uppercase">Max Drawdown</div>
 </div>
 </div>

 {/* Rationale */}
 <div className="p-4 rounded-xl bg-white/50 border border-white/40 mb-6">
 <p className="text-sm text-slate-700">{recommendation.rationale}</p>
 </div>

 {/* Target Allocation */}
 <div className="mb-6">
 <h4 className="text-sm font-bold text-slate-900 mb-3">Recommended Asset Allocation</h4>

 {/* Allocation Bar */}
 <div className="h-8 rounded-xl overflow-hidden flex mb-3">
 {target.buckets.map((bucket, idx) => {
 const colors = [
 'bg-blue-500', 'bg-indigo-500', 'bg-purple-500',
 'bg-emerald-500', 'bg-teal-500', 'bg-amber-500', 'bg-slate-400',
 ];
 return (
 <div
 key={bucket.assetClass}
 className={`${colors[idx % colors.length]} flex items-center justify-center text-[9px] font-bold text-white/90 transition-all`}
 style={{ width: `${bucket.targetPct}%` }}
 title={`${bucket.assetClass}: ${bucket.targetPct}%`}
 >
 {bucket.targetPct >= 10 ? `${bucket.targetPct}%` : ''}
 </div>
 );
 })}
 </div>

 {/* Bucket Details */}
 <div className="space-y-2">
 {target.buckets.map((bucket, idx) => {
 const colors = [
 'bg-blue-500', 'bg-indigo-500', 'bg-purple-500',
 'bg-emerald-500', 'bg-teal-500', 'bg-amber-500', 'bg-slate-400',
 ];
 return (
 <div key={bucket.assetClass} className="flex items-center gap-3 p-2 rounded-lg bg-white/30">
 <div className={`w-3 h-3 rounded-sm ${colors[idx % colors.length]}`} />
 <div className="flex-1 min-w-0">
 <div className="text-xs font-medium text-slate-900">{bucket.assetClass}</div>
 <div className="text-[10px] text-slate-500 truncate">
 {bucket.examples.join(', ')}
 </div>
 </div>
 <div className="text-right">
 <span className="text-sm font-bold text-slate-900">{bucket.targetPct}%</span>
 <span className="text-[10px] text-slate-400 block">
 {bucket.minPct}-{bucket.maxPct}%
 </span>
 </div>
 </div>
 );
 })}
 </div>
 </div>

 {/* Time Horizon */}
 <div className={`p-3 rounded-xl ${profileBg(recommendation.profile)} border mb-4`}>
 <div className="flex items-center gap-2">
 <span className="text-sm">📅</span>
 <span className="text-xs font-medium">
 Recommended Time Horizon: <strong>{recommendation.timeHorizon}</strong>
 </span>
 </div>
 </div>

 {/* Actions */}
 <div className="flex gap-3">
 <button
 onClick={handleRestart}
 className="px-4 py-2 text-sm font-medium rounded-xl border border-white/40 bg-white/30 text-slate-700 hover:bg-white/50 transition-all"
 >
 Retake Quiz
 </button>
 <button
 onClick={() => onComplete?.(recommendation)}
 className="flex-1 px-4 py-2 text-sm font-semibold rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-md hover:shadow-lg transition-all"
 >
 Apply to Portfolio →
 </button>
 </div>
 </div>
 );
 }

 return null;
}
