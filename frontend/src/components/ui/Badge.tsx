import type { ReactNode } from 'react';

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'outline';

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-white/60 dark:bg-white/10 text-slate-700 dark:text-slate-200 border border-white/60 dark:border-white/10 backdrop-blur-md shadow-sm',
  success: 'bg-emerald-500/12 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20 backdrop-blur-md shadow-sm',
  warning: 'bg-sky-500/14 dark:bg-sky-500/15 text-sky-700 dark:text-sky-300 border border-sky-500/20 backdrop-blur-md shadow-sm',
  danger: 'bg-red-500/12 dark:bg-red-500/15 text-red-700 dark:text-red-300 border border-red-500/18 backdrop-blur-md shadow-sm',
  info: 'bg-blue-500/12 dark:bg-blue-500/15 text-blue-700 dark:text-blue-300 border border-blue-500/18 backdrop-blur-md shadow-sm',
  outline: 'bg-transparent text-slate-600 dark:text-slate-300 border border-slate-300/60 dark:border-white/10 backdrop-blur-sm',
};

interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  className?: string;
}

export default function Badge({ children, variant = 'default', size = 'sm', className = '' }: BadgeProps) {
  const sizeClasses = size === 'sm' ? 'px-2.5 py-1 text-[11px] font-bold tracking-wide' : 'px-3 py-1 text-xs font-bold tracking-wide';
  return (
    <span className={`inline-flex items-center rounded-full ${variantStyles[variant]} ${sizeClasses} ${className}`}>
      {children}
    </span>
  );
}
