import { useState, useEffect, useRef, useCallback } from 'react';

interface TourStep {
  target: string; // CSS selector or element ID
  title: string;
  content: string;
  placement?: 'top' | 'bottom' | 'left' | 'right';
  highlightPadding?: number;
}

const DEFAULT_STEPS: TourStep[] = [
  {
    target: '[data-tour="sidebar"]',
    title: 'Navigation Sidebar',
    content: 'Access all pages from the grouped sidebar. Sections collapse to keep things tidy.',
    placement: 'right' },
  {
    target: '[data-tour="search"]',
    title: 'Smart Search',
    content: 'Type naturally — "show me risk dashboard" — and we\'ll find it for you. Press / to focus.',
    placement: 'bottom' },
  {
    target: '[data-tour="portfolio-selector"]',
    title: 'Portfolio Selector',
    content: 'Switch between portfolios here. Your selection persists across all pages.',
    placement: 'bottom' },
  {
    target: '[data-tour="quick-actions"]',
    title: 'Quick Actions',
    content: 'Jump straight to creating a portfolio, running an optimization, or viewing the audit log.',
    placement: 'left' },
  {
    target: '[data-tour="health-score"]',
    title: 'Portfolio Health Score',
    content: 'Your single-number health metric. Click to see the full breakdown across 5 dimensions.',
    placement: 'top' },
  {
    target: '[data-tour="shortcuts"]',
    title: 'Keyboard Shortcuts',
    content: 'Press ? anywhere to see all available shortcuts. Power users love this.',
    placement: 'bottom' },
];

interface GuidedTourProps {
  steps?: TourStep[];
  onComplete?: () => void;
  storageKey?: string;
}

function getRect(selector: string): DOMRect | null {
  const el = document.querySelector(selector);
  if (!el) return null;
  return el.getBoundingClientRect();
}

function calculatePosition(targetRect: DOMRect, placement: string, padding = 8) {
  const scrollTop = window.scrollY;
  const scrollLeft = window.scrollX;

  switch (placement) {
    case 'top':
      return {
        top: targetRect.top + scrollTop - padding,
        left: targetRect.left + scrollLeft + targetRect.width / 2,
        transform: 'translate(-50%, -100%)' };
    case 'bottom':
      return {
        top: targetRect.bottom + scrollTop + padding,
        left: targetRect.left + scrollLeft + targetRect.width / 2,
        transform: 'translate(-50%, 0)' };
    case 'left':
      return {
        top: targetRect.top + scrollTop + targetRect.height / 2,
        left: targetRect.left + scrollLeft - padding,
        transform: 'translate(-100%, -50%)' };
    case 'right':
    default:
      return {
        top: targetRect.top + scrollTop + targetRect.height / 2,
        left: targetRect.left + scrollLeft + targetRect.width + padding,
        transform: 'translate(0, -50%)' };
  }
}

export default function GuidedTour({
  steps = DEFAULT_STEPS,
  onComplete,
  storageKey = 'quantive_tour_completed' }: GuidedTourProps) {
  const [active, setActive] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [position, setPosition] = useState({ top: 0, left: 0, transform: '' });
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  // Check if tour was already completed
  useEffect(() => {
    const completed = localStorage.getItem(storageKey);
    if (!completed) {
      // Auto-start after a short delay
      const timer = setTimeout(() => setActive(true), 1500);
      return () => clearTimeout(timer);
    }
  }, [storageKey]);

  // Calculate position when step changes
  useEffect(() => {
    if (!active) return;
    const step = steps[currentStep];
    if (!step) return;

    const updatePosition = () => {
      const rect = getRect(step.target);
      if (rect) {
        setTargetRect(rect);
        setPosition(calculatePosition(rect, step.placement || 'bottom', step.highlightPadding || 8));
      }
    };

    updatePosition();
    window.addEventListener('resize', updatePosition);
    window.addEventListener('scroll', updatePosition);
    return () => {
      window.removeEventListener('resize', updatePosition);
      window.removeEventListener('scroll', updatePosition);
    };
  }, [active, currentStep, steps]);

  const handleNext = useCallback(() => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(i => i + 1);
    } else {
      handleComplete();
    }
  }, [currentStep, steps.length]);

  const handlePrev = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep(i => i - 1);
    }
  }, [currentStep]);

  const handleComplete = useCallback(() => {
    setActive(false);
    localStorage.setItem(storageKey, 'true');
    onComplete?.();
  }, [storageKey, onComplete]);

  const handleSkip = useCallback(() => {
    handleComplete();
  }, [handleComplete]);

  // Keyboard navigation
  useEffect(() => {
    if (!active) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === 'Enter') handleNext();
      else if (e.key === 'ArrowLeft') handlePrev();
      else if (e.key === 'Escape') handleSkip();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [active, handleNext, handlePrev, handleSkip]);

  if (!active || currentStep >= steps.length) return null;

  const step = steps[currentStep];

  return (
    <>
      {/* Backdrop overlay */}
      <div
        className="fixed inset-0 z-[9998] bg-black/30 transition-all duration-300"
        onClick={handleSkip}
      />

      {/* Highlight ring around target */}
      {targetRect && (
        <div
          className="fixed z-[9998] border-2 border-blue-400 rounded-xl shadow-[0_0_0_9999px_rgba(0,0,0,0.3)] transition-all duration-300"
          style={{
            top: targetRect.top - 4,
            left: targetRect.left - 4,
            width: targetRect.width + 8,
            height: targetRect.height + 8 }}
        />
      )}

      {/* Tooltip */}
      <div
        ref={tooltipRef}
        className="fixed z-[9999] w-80 glass-strong rounded-2xl shadow-2xl border border-white/30 overflow-hidden animate-glass-in"
        style={{
          top: position.top,
          left: position.left,
          transform: position.transform }}
      >
        {/* Progress bar */}
        <div className="h-1 bg-white/20">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 transition-all duration-300"
            style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
          />
        </div>

        <div className="p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-blue-600 bg-blue-50 rounded-full px-2 py-0.5">
                {currentStep + 1} of {steps.length}
              </span>
            </div>
            <button
              onClick={handleSkip}
              className="text-xs text-slate-400 hover:text-slate-600 transition-colors"
            >
              Skip tour
            </button>
          </div>

          <h3 className="text-base font-bold text-slate-900 mb-2">{step.title}</h3>
          <p className="text-sm text-slate-600 leading-relaxed">{step.content}</p>

          <div className="flex items-center justify-between mt-5">
            <button
              onClick={handlePrev}
              disabled={currentStep === 0}
              className="text-sm font-medium text-slate-500 hover:text-slate-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              ← Previous
            </button>
            <div className="flex items-center gap-2">
              {/* Step dots */}
              {steps.map((_, i) => (
                <div
                  key={i}
                  className={`w-1.5 h-1.5 rounded-full transition-all ${
                    i === currentStep ? 'bg-blue-500 scale-125' : i < currentStep ? 'bg-blue-300' : 'bg-slate-200'
                  }`}
                />
              ))}
            </div>
            <button
              onClick={handleNext}
              className="glass-btn-primary text-sm px-4 py-1.5"
            >
              {currentStep === steps.length - 1 ? 'Finish' : 'Next →'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
