import { useState, useEffect, useCallback } from 'react';
import { events } from '../lib/analytics';
import type { TourStep } from '../hooks/useOnboardingTour';

interface OnboardingTourProps {
  isActive: boolean;
  currentStep: TourStep | null;
  currentStepIndex: number;
  totalSteps: number;
  position: { top: number; left: number } | null;
  isFirst: boolean;
  isLast: boolean;
  onNext: () => void;
  onPrev: () => void;
  onSkip: () => void;
}

export default function OnboardingTour({
  isActive,
  currentStep,
  currentStepIndex,
  totalSteps,
  position,
  isFirst,
  isLast,
  onNext,
  onPrev,
  onSkip }: OnboardingTourProps) {
  const [visible, setVisible] = useState(false);

  // Fade in/out animation
  useEffect(() => {
    if (isActive) {
      requestAnimationFrame(() => setVisible(true));
    } else {
      setVisible(false);
    }
  }, [isActive]);

  const handleNext = useCallback(() => {
    setVisible(false);
    setTimeout(() => {
      onNext();
      requestAnimationFrame(() => setVisible(true));
    }, 150);
  }, [onNext]);

  const handlePrev = useCallback(() => {
    setVisible(false);
    setTimeout(() => {
      onPrev();
      requestAnimationFrame(() => setVisible(true));
    }, 150);
  }, [onPrev]);

  if (!isActive || !currentStep || !position) return null;

  return (
    <>
      {/* Backdrop overlay */}
      <div
        className={`fixed inset-0 z-[10000] bg-slate-900/30 backdrop-blur-[2px] transition-opacity duration-200 ${visible ? 'opacity-100' : 'opacity-0'}`}
        onClick={onSkip}
      />

      {/* Tooltip */}
      <div
        className={`fixed z-[10001] w-72 transition-all duration-200 ${visible ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}`}
        style={{
          top: `${position.top}px`,
          left: `${Math.min(position.left, window.innerWidth - 300)}px`,
          transform: 'translate(-50%, 0)' }}
        role="dialog"
        aria-label={`Tour step ${currentStepIndex + 1} of ${totalSteps}`}
      >
        <div className="glass-strong rounded-2xl shadow-2xl border border-white/40 overflow-hidden">
          {/* Step indicator */}
          <div className="px-4 pt-3 flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              {Array.from({ length: totalSteps }, (_, i) => (
                <div
                  key={i}
                  className={`h-1 rounded-full transition-all duration-300 ${
                    i === currentStepIndex
                      ? 'w-5 bg-blue-500'
                      : i < currentStepIndex
                        ? 'w-2 bg-blue-300'
                        : 'w-2 bg-slate-200'
                  }`}
                />
              ))}
            </div>
            <span className="text-[10px] font-medium text-slate-400">
              {currentStepIndex + 1}/{totalSteps}
            </span>
          </div>

          {/* Content */}
          <div className="px-4 py-3">
            <h3 className="text-sm font-bold text-slate-900">{currentStep.title}</h3>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">{currentStep.content}</p>
          </div>

          {/* Actions */}
          <div className="px-4 pb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              {!isFirst && (
                <button
                  onClick={handlePrev}
                  className="text-xs text-slate-400 hover:text-slate-600 transition-colors"
                >
                  Back
                </button>
              )}
              <button
                onClick={onSkip}
                className="text-xs text-slate-400 hover:text-slate-600 transition-colors"
              >
                Skip tour
              </button>
            </div>
            <button
              onClick={handleNext}
              className="px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
            >
              {isLast ? 'Finish' : 'Next'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
