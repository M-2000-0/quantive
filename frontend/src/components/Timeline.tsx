interface TimelineEvent {
  id: string;
  type: 'create' | 'update' | 'delete' | 'optimize' | 'export' | 'comment' | 'alert' | 'system';
  title: string;
  description?: string;
  actor: string;
  timestamp: string;
  metadata?: Record<string, string>;
}

interface TimelineProps {
  events: TimelineEvent[];
  title?: string;
}

const TYPE_CONFIG: Record<string, { icon: string; color: string; bg: string }> = {
  create: { icon: '➕', color: 'text-green-400', bg: 'bg-green-500/10' },
  update: { icon: '✏️', color: 'text-blue-400', bg: 'bg-blue-500/10' },
  delete: { icon: '🗑️', color: 'text-red-400', bg: 'bg-red-500/10' },
  optimize: { icon: 'Zap', color: 'text-purple-400', bg: 'bg-purple-500/10' },
  export: { icon: 'Upload', color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
  comment: { icon: 'MessageSquare', color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
  alert: { icon: '🔔', color: 'text-orange-400', bg: 'bg-orange-500/10' },
  system: { icon: 'Settings', color: 'text-slate-400', bg: 'bg-slate-500/10' } };

export default function Timeline({ events, title = 'Activity Timeline' }: TimelineProps) {
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-white/80">{title}</h3>
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-[15px] top-0 bottom-0 w-px bg-white/10" />

        <div className="space-y-1">
          {events.map((event) => {
            const config = TYPE_CONFIG[event.type] || TYPE_CONFIG.system;
            return (
              <div key={event.id} className="flex gap-3 py-2 group hover:bg-white/[0.02] rounded-xl px-2 transition-colors">
                <div className={`relative z-10 w-8 h-8 rounded-xl ${config.bg} flex items-center justify-center text-sm flex-shrink-0`}>
                  {config.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white/80">{event.title}</span>
                    <span className="text-[10px] text-white/30">{event.timestamp}</span>
                  </div>
                  {event.description && (
                    <p className="text-xs text-white/40 mt-0.5 truncate">{event.description}</p>
                  )}
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] text-white/30">by {event.actor}</span>
                    {event.metadata && Object.entries(event.metadata).map(([k, v]) => (
                      <span key={k} className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-white/40">
                        {k}: {v}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
