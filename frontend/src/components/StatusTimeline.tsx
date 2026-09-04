interface Step {
  id: string;
  label: string;
  status: 'completed' | 'active' | 'pending' | 'error';
  timestamp?: string;
  duration?: string;
}

interface StatusTimelineProps {
  steps: Step[];
  title?: string;
}

export default function StatusTimeline({ steps, title }: StatusTimelineProps) {
  return (
    <div className="glass-card p-4">
      {title && <h3 className="text-sm font-semibold text-white/80 mb-4">{title}</h3>}
      <div className="space-y-0">
        {steps.map((step, idx) => {
          const isLast = idx === steps.length - 1;
          const statusConfig = {
            completed: { dot: 'bg-green-500', line: 'bg-green-500', text: 'text-white' },
            active: { dot: 'bg-blue-500 animate-pulse', line: 'bg-white/10', text: 'text-white' },
            pending: { dot: 'bg-white/20', line: 'bg-white/10', text: 'text-white/40' },
            error: { dot: 'bg-red-500', line: 'bg-red-500/30', text: 'text-red-400' } };
          const config = statusConfig[step.status];

          return (
            <div key={step.id} className="flex gap-3">
              {/* Dot + Line */}
              <div className="flex flex-col items-center">
                <div className={`w-3 h-3 rounded-full ${config.dot} flex-shrink-0 mt-1.5`}>
                  {step.status === 'active' && (
                    <div className="w-3 h-3 rounded-full bg-blue-500 animate-ping" />
                  )}
                </div>
                {!isLast && <div className={`w-px flex-1 ${config.line} my-1`} />}
              </div>

              {/* Content */}
              <div className={`pb-4 ${config.text}`}>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{step.label}</span>
                  {step.duration && <span className="text-[10px] text-white/30">({step.duration})</span>}
                </div>
                {step.timestamp && <span className="text-[10px] text-white/30">{step.timestamp}</span>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
