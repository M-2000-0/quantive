type ProgressVariant = 'default' | 'success' | 'warning' | 'danger';
type ProgressSize = 'sm' | 'md' | 'lg';

interface ProgressBarProps {
  value: number;
  label?: string;
  size?: ProgressSize;
  showPercentage?: boolean;
  variant?: ProgressVariant;
}

const variantStyles: Record<ProgressVariant, string> = {
  default: 'bg-gradient-to-r from-blue-600 to-indigo-600',
  success: 'bg-gradient-to-r from-emerald-500 to-teal-600',
  warning: 'bg-gradient-to-r from-amber-500 to-orange-500',
  danger: 'bg-gradient-to-r from-red-500 to-rose-600',
};

const sizeStyles: Record<ProgressSize, string> = {
  sm: 'rounded-full',
  md: 'rounded-full',
  lg: 'rounded-full',
};

export default function ProgressBar({
  value,
  label,
  size = 'md',
  showPercentage = false,
  variant = 'default',
}: ProgressBarProps) {
  const clampedValue = Math.min(100, Math.max(0, value * 100));

  return (
    <div className="w-full">
      {(label || showPercentage) && (
        <div className="flex items-center justify-between mb-2">
          {label && <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">{label}</span>}
          {showPercentage && (
            <span className="text-xs font-bold tabular-nums px-2 py-0.5 rounded-full bg-white/60 dark:bg-white/10 border border-white/60 dark:border-white/10 backdrop-blur-md text-slate-700 dark:text-slate-300 shadow-sm">{clampedValue.toFixed(0)}%</span>
          )}
        </div>
      )}
      <div className={`liquid-progress ${sizeStyles[size]}`} style={{ height: size === 'sm' ? '8px' : size === 'lg' ? '14px' : '10px' }}>
        <div
          className={`liquid-progress-fill ${variantStyles[variant]} ${sizeStyles[size]}`}
          style={{ width: `${clampedValue}%` }}
          role="progressbar"
          aria-valuenow={clampedValue}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
    </div>
  );
}
