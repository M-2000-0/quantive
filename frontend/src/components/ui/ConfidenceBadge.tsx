type ConfidenceLevel = 'high' | 'medium' | 'low';

interface ConfidenceBadgeProps {
  score: number; // 0-100
  showLabel?: boolean;
  size?: 'sm' | 'md';
}

const levelConfig: Record<ConfidenceLevel, { label: string; gradient: string; text: string; ring: string }> = {
  high: {
    label: 'High Confidence',
    gradient: 'from-emerald-500 to-teal-500',
    text: 'text-emerald-700 dark:text-emerald-300',
    ring: 'ring-emerald-500/20',
  },
  medium: {
    label: 'Medium Confidence',
    gradient: 'from-amber-500 to-orange-500',
    text: 'text-amber-700 dark:text-amber-300',
    ring: 'ring-amber-500/20',
  },
  low: {
    label: 'Low Confidence',
    gradient: 'from-red-500 to-rose-500',
    text: 'text-red-700 dark:text-red-300',
    ring: 'ring-red-500/20',
  },
};

function getLevel(score: number): ConfidenceLevel {
  if (score >= 75) return 'high';
  if (score >= 45) return 'medium';
  return 'low';
}

export default function ConfidenceBadge({ score, showLabel = true, size = 'sm' }: ConfidenceBadgeProps) {
  const level = getLevel(score);
  const config = levelConfig[level];
  const clamped = Math.min(100, Math.max(0, score));

  return (
    <div className={`inline-flex items-center gap-2 ${size === 'sm' ? 'text-xs' : 'text-sm'}`}>
      {/* Mini circular progress */}
      <div className="relative flex-shrink-0">
        <svg
          className={`${size === 'sm' ? 'w-8 h-8' : 'w-10 h-10'} -rotate-90`}
          viewBox="0 0 36 36"
        >
          {/* Track */}
          <circle
            cx="18" cy="18" r="15"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            className="text-white/40 dark:text-white/10"
          />
          {/* Fill */}
          <circle
            cx="18" cy="18" r="15"
            fill="none"
            stroke="url(#conf-gradient)"
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray={`${clamped * 0.942} 100`}
            className="transition-all duration-700 ease-[cubic-bezier(0.4,0,0.2,1)]"
          />
          <defs>
            <linearGradient id="conf-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" className={`${config.gradient}`} stopColor="currentColor" />
              <stop offset="100%" className={`${config.gradient}`} stopColor="currentColor" />
            </linearGradient>
          </defs>
        </svg>
        <span className={`absolute inset-0 flex items-center justify-center font-bold tabular-nums ${config.text} ${size === 'sm' ? 'text-[9px]' : 'text-[10px]'}`}>
          {clamped}
        </span>
      </div>

      {showLabel && (
        <span className={`inline-flex items-center rounded-full px-2 py-0.5 font-semibold backdrop-blur-md border border-white/40 shadow-sm bg-white/60 dark:bg-white/10 ${config.text} ring-1 ${config.ring}`}>
          {config.label}
        </span>
      )}
    </div>
  );
}
