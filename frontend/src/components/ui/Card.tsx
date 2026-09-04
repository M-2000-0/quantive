import type { CSSProperties, ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  padding?: boolean;
  style?: CSSProperties;
}

export default function Card({ children, className = '', padding = true, style }: CardProps) {
  return (
    <div
      style={style}
      className={`
        glass-card glass-hover glass-shimmer
        ${padding ? 'p-6' : ''}
        ${className}
      `}
    >
      {children}
    </div>
  );
}

interface CardHeaderProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}

export function CardHeader({ title, subtitle, action }: CardHeaderProps) {
  return (
    <div className="flex items-start justify-between mb-5">
      <div>
        <h3 className="text-[15px] font-semibold tracking-tight text-slate-900 dark:text-slate-100">{title}</h3>
        {subtitle && (
          <p className="mt-1 text-[13px] leading-snug text-slate-500 dark:text-slate-400">{subtitle}</p>
        )}
      </div>
      {action && <div className="ml-4 flex-shrink-0">{action}</div>}
    </div>
  );
}
