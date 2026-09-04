// ── useGlassEffects Hook ─────────────────────────────────────────────
// Provides cursor-tracking for dynamic refraction, ambient lighting
// based on time-of-day, and context-adaptive glass intelligence.

import { useEffect, useCallback, useRef, useState } from 'react';

// ── Cursor Tracker ───────────────────────────────────────────────────
// Tracks mouse position and updates CSS custom properties on glass
// elements for dynamic refraction effects.

export function useGlassCursor() {
  const rafRef = useRef<number | null>(null);
  const posRef = useRef({ x: 0, y: 0 });

  const handleMouseMove = useCallback((e: MouseEvent) => {
    posRef.current = { x: e.clientX, y: e.clientY };

    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      document.documentElement.style.setProperty('--cursor-x', `${posRef.current.x}px`);
      document.documentElement.style.setProperty('--cursor-y', `${posRef.current.y}px`);

      // Normalize 0-1 for gradient calculations
      const nx = posRef.current.x / window.innerWidth;
      const ny = posRef.current.y / window.innerHeight;
      document.documentElement.style.setProperty('--cursor-nx', `${nx}`);
      document.documentElement.style.setProperty('--cursor-ny', `${ny}`);
    });
  }, []);

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [handleMouseMove]);
}

// ── Ambient Lighting ─────────────────────────────────────────────────
// Adjusts CSS variables based on time-of-day:
//   Morning (6-10): warm, golden light
//   Day (10-16): bright, neutral
//   Evening (16-20): amber, warm
//   Night (20-6): cool, dimmed

export type TimePeriod = 'morning' | 'day' | 'evening' | 'night';

export function getTimePeriod(): TimePeriod {
  const hour = new Date().getHours();
  if (hour >= 6 && hour < 10) return 'morning';
  if (hour >= 10 && hour < 16) return 'day';
  if (hour >= 16 && hour < 20) return 'evening';
  return 'night';
}

const TIME_CONFIG: Record<TimePeriod, {
  ambientStrength: number;
  specularOpacity: number;
  blurMultiplier: number;
  pageGradient: string;
  glassBgLight: string;
  label: string;
}> = {
  morning: {
    ambientStrength: 0.2,
    specularOpacity: 0.8,
    blurMultiplier: 1.0,
    pageGradient: 'linear-gradient(135deg, #fef3c7 0%, #fff7ed 25%, #fef9c3 50%, #fefce8 75%, #fffbeb 100%)',
    glassBgLight: 'rgba(255, 255, 255, 0.6)',
    label: '☀️ Morning Light',
  },
  day: {
    ambientStrength: 0.15,
    specularOpacity: 0.7,
    blurMultiplier: 1.0,
    pageGradient: 'linear-gradient(135deg, #e0e7ff 0%, #f0f4ff 25%, #e8f4f8 50%, #f0f0ff 75%, #e5e7eb 100%)',
    glassBgLight: 'rgba(255, 255, 255, 0.55)',
    label: '🌤️ Day Light',
  },
  evening: {
    ambientStrength: 0.18,
    specularOpacity: 0.6,
    blurMultiplier: 0.95,
    pageGradient: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 25%, #1e3a5f 50%, #1e293b 75%, #0f172a 100%)',
    glassBgLight: 'rgba(30, 27, 75, 0.6)',
    label: '🌅 Evening',
  },
  night: {
    ambientStrength: 0.08,
    specularOpacity: 0.25,
    blurMultiplier: 0.9,
    pageGradient: 'linear-gradient(135deg, #0a0a14 0%, #08091a 25%, #0b0f1a 50%, #0d0d1f 75%, #06060e 100%)',
    glassBgLight: 'rgba(15, 23, 42, 0.55)',
    label: '🌙 Night Mode',
  },
};

export function useAmbientLighting() {
  const [period, setPeriod] = useState<TimePeriod>(getTimePeriod);

  useEffect(() => {
    const interval = setInterval(() => {
      setPeriod(getTimePeriod());
    }, 60000); // Check every minute
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const config = TIME_CONFIG[period];
    const root = document.documentElement;
    root.style.setProperty('--ambient-strength', String(config.ambientStrength));
    root.style.setProperty('--specular-opacity', String(config.specularOpacity));
  }, [period]);

  return { period, config: TIME_CONFIG[period] };
}

// ── Glass Depth Tracker ──────────────────────────────────────────────
// Assigns depth layers to glass elements based on scroll position.
// Elements further from viewport get heavier blur.

export function useGlassDepth(containerRef: React.RefObject<HTMLElement | null>) {
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const children = container.querySelectorAll('.glass, .glass-card');
      const scrollTop = window.scrollY;

      children.forEach((el) => {
        const rect = el.getBoundingClientRect();
        const viewportCenter = window.innerHeight / 2;
        const distFromCenter = Math.abs(rect.top + rect.height / 2 - viewportCenter);
        const maxDist = window.innerHeight;
        const factor = Math.min(distFromCenter / maxDist, 1);

        // Subtle blur increase for elements far from center
        const extraBlur = factor * 2; // 0-2px extra
        (el as HTMLElement).style.setProperty(
          '--depth-blur',
          `${extraBlur}px`
        );
      });
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, [containerRef]);
}

// ── Ripple Effect ────────────────────────────────────────────────────
// Adds expanding ripple on click at mouse position.

export function useGlassRipple() {
  const handleRipple = useCallback((e: React.MouseEvent<HTMLElement>) => {
    const el = e.currentTarget;
    const rect = el.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    el.style.setProperty('--ripple-x', `${x}%`);
    el.style.setProperty('--ripple-y', `${y}%`);
  }, []);

  return { onRipple: handleRipple };
}

// ── Combined Hook ────────────────────────────────────────────────────

export function useLiquidGlass() {
  useGlassCursor();
  const { period, config } = useAmbientLighting();

  return {
    period,
    timeConfig: config,
    isDarkTime: period === 'evening' || period === 'night',
  };
}
