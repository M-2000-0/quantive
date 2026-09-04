import { useState, useEffect, useCallback } from 'react';
import { track, events } from '../lib/analytics';

export interface TourStep {
  id: string;
  target: string;       // CSS selector for the element to highlight
  title: string;
  content: string;
  placement?: 'top' | 'bottom' | 'left' | 'right';
  action?: 'click' | 'type' | 'observe';
}

export const DEFAULT_TOUR_STEPS: TourStep[] = [
  {
    id: 'welcome',
    target: '#main-content',
    title: 'Welcome to Quantive',
    content: 'This is your portfolio dashboard. Let\'s take a quick tour of the key features.',
    placement: 'bottom',
  },
  {
    id: 'sidebar',
    target: 'nav',
    title: 'Navigation',
    content: 'Use the sidebar to navigate between portfolios, optimizations, risk analysis, and more.',
    placement: 'right',
  },
  {
    id: 'search',
    target: '[aria-label="Open command palette"]',
    title: 'Quick Search',
    content: 'Press ⌘K (or Ctrl+K) to open the command palette. Search for any page, portfolio, or optimization instantly.',
    placement: 'bottom',
  },
  {
    id: 'theme',
    target: '[title="Toggle theme"]',
    title: 'Light & Dark Mode',
    content: 'Toggle between light and dark themes. Your preference is saved automatically.',
    placement: 'left',
  },
  {
    id: 'notifications',
    target: '[aria-label*="notification"]',
    title: 'Notifications',
    content: 'Get real-time updates on optimization jobs, market data alerts, and system status.',
    placement: 'left',
  },
  {
    id: 'portfolio-cta',
    target: 'a[href="/portfolios"]',
    title: 'Your Portfolios',
    content: 'Create and manage your debt portfolios. Import from CSV, use demo data, or add instruments manually.',
    placement: 'right',
  },
];

const TOUR_STORAGE_KEY = 'quantive:onboarding-tour-completed';

function getStepPosition(target: string, placement: string): { top: number; left: number } {
  const el = document.querySelector(target);
  if (!el) return { top: 100, left: 200 };

  const rect = el.getBoundingClientRect();
  const scrollY = window.scrollY;
  const scrollX = window.scrollX;

  switch (placement) {
    case 'bottom':
      return { top: rect.bottom + scrollY + 12, left: rect.left + scrollX + rect.width / 2 };
    case 'top':
      return { top: rect.top + scrollY - 12, left: rect.left + scrollX + rect.width / 2 };
    case 'left':
      return { top: rect.top + scrollY + rect.height / 2, left: rect.left + scrollX - 12 };
    case 'right':
      return { top: rect.top + scrollY + rect.height / 2, left: rect.right + scrollX + 12 };
    default:
      return { top: rect.bottom + scrollY + 12, left: rect.left + scrollX + rect.width / 2 };
  }
}

export function useOnboardingTour(steps: TourStep[] = DEFAULT_TOUR_STEPS) {
  const [isActive, setIsActive] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [completed, setCompleted] = useState(() => {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem(TOUR_STORAGE_KEY) === 'true';
  });

  const currentStep = steps[currentStepIndex];
  const position = currentStep ? getStepPosition(currentStep.target, currentStep.placement || 'bottom') : null;

  const start = useCallback(() => {
    events.onboardingStarted();
    setIsActive(true);
    setCurrentStepIndex(0);
  }, []);

  const next = useCallback(() => {
    if (currentStepIndex < steps.length - 1) {
      setCurrentStepIndex(prev => prev + 1);
    } else {
      // Tour complete
      setCompleted(true);
      setIsActive(false);
      localStorage.setItem(TOUR_STORAGE_KEY, 'true');
      events.onboardingCompleted(steps.length);
    }
  }, [currentStepIndex, steps.length]);

  const prev = useCallback(() => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(prev => prev - 1);
    }
  }, [currentStepIndex]);

  const skip = useCallback(() => {
    setCompleted(true);
    setIsActive(false);
    localStorage.setItem(TOUR_STORAGE_KEY, 'true');
    events.onboardingSkipped(currentStepIndex);
  }, [currentStepIndex]);

  const reset = useCallback(() => {
    localStorage.removeItem(TOUR_STORAGE_KEY);
    setCompleted(false);
    setIsActive(false);
    setCurrentStepIndex(0);
  }, []);

  // Scroll target into view when step changes
  useEffect(() => {
    if (!isActive || !currentStep) return;
    const el = document.querySelector(currentStep.target);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [isActive, currentStepIndex, currentStep]);

  // Close on Escape
  useEffect(() => {
    if (!isActive) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') skip();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [isActive, skip]);

  return {
    isActive,
    currentStep,
    currentStepIndex,
    totalSteps: steps.length,
    position,
    completed,
    start,
    next,
    prev,
    skip,
    reset,
    isFirst: currentStepIndex === 0,
    isLast: currentStepIndex === steps.length - 1,
  };
}
