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
  sm: 'h-2',
  md: 'h-2.5',
  lg: 'h-3.5',
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
          {label && <span className="text-sm font-semibold text-slate-800">{label}</span>}
          {showPercentage && (
            <span className="text-xs font-bold tabular-nums px-2 py-0.5 rounded-full bg-white/60 border border-white/60 backdrop-blur-md text-slate-700 shadow-sm">{clampedValue.toFixed(0)}%</span>
          )}
        </div>
      )}
      <div className={`w-full bg-white/50 backdrop-blur-md border border-white/50 rounded-full overflow-hidden shadow-inner ${sizeStyles[size]}`}>
        <div
          className={`${variantStyles[variant]} rounded-full transition-all duration-700 ease-[cubic-bezier(0.2,0.8,0.2,1)] shadow-sm relative overflow-hidden ${sizeStyles[size]}`}
          style={{ width: `${clampedValue}%` }}
          role="progressbar"
          aria-valuenow={clampedValue}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div className="absolute inset-0 bg-gradient-to-b from-white/25 to-transparent pointer-events-none" />
        </div>
      </div>
    </div>
  );
}
