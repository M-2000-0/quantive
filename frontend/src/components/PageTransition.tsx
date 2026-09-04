import { useEffect, useState, type ReactNode } from 'react';
import { useLocation } from 'react-router-dom';

interface PageTransitionProps {
  children: ReactNode;
}

/**
 * Wraps page content with a liquid slide-up + fade-in animation on route changes.
 * Uses CSS animation classes from index.css (animate-glass-in).
 */
export default function PageTransition({ children }: PageTransitionProps) {
  const { pathname } = useLocation();
  const [displayChildren, setDisplayChildren] = useState(children);
  const [transitionStage, setTransitionStage] = useState<'enter' | 'idle'>('enter');

  useEffect(() => {
    // When route changes, trigger exit → enter
    setTransitionStage('enter');
    setDisplayChildren(children);

    // Allow the enter animation to play
    const frame = requestAnimationFrame(() => {
      setTransitionStage('idle');
    });
    return () => cancelAnimationFrame(frame);
  }, [pathname, children]);

  return (
    <div
      className={`
        transition-opacity duration-300 ease-[cubic-bezier(0.4,0,0.2,1)]
        ${transitionStage === 'enter' ? 'opacity-0 translate-y-2' : 'opacity-100 translate-y-0'}
      `}
      style={{ willChange: 'opacity, transform' }}
    >
      {displayChildren}
    </div>
  );
}
