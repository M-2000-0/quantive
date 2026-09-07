import { useCallback, useRef } from 'react';

/**
 * Tracks mouse position on an element and sets --ripple-x / --ripple-y
 * CSS custom properties so the .glass-ripple::before radial gradient follows
 * the cursor.  Returns a ref callback and onMouseMove handler.
 *
 * Usage:
 *   const { ref, onMouseMove } = useGlassRipple<HTMLDivElement>();
 *   <div ref={ref} onMouseMove={onMouseMove} className="glass-ripple">
 */
export function useGlassRipple<T extends HTMLElement>() {
  const nodeRef = useRef<T | null>(null);

  const setRef = useCallback((node: T | null) => {
    nodeRef.current = node;
  }, []);

  const onMouseMove = useCallback((e: React.MouseEvent<T>) => {
    const el = e.currentTarget;
    const rect = el.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    el.style.setProperty('--ripple-x', `${x}%`);
    el.style.setProperty('--ripple-y', `${y}%`);
  }, []);

  return { ref: setRef, onMouseMove } as {
    ref: (node: T | null) => void;
    onMouseMove: (e: React.MouseEvent<T>) => void;
  };
}
