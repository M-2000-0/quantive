import { useState } from 'react';
import { Card } from './ui';
import { Badge } from './ui';
import { Button } from './ui';

interface Schedule {
  id: string;
  name: string;
  type: 'report' | 'optimization' | 'data_sync' | 'notification';
  frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly';
  time: string;
  enabled: boolean;
  lastRun?: string;
  nextRun: string;
}

const MOCK_SCHEDULES: Schedule[] = [
  { id: '1', name: 'Weekly Portfolio Summary', type: 'report', frequency: 'weekly', time: 'Monday 09:00', enabled: true, lastRun: '2026-08-18', nextRun: '2026-08-25' },
  { id: '2', name: 'Daily Market Data Refresh', type: 'data_sync', frequency: 'daily', time: '06:00 UTC', enabled: true, lastRun: '2026-08-24', nextRun: '2026-08-25' },
  { id: '3', name: 'Monthly Optimization', type: 'optimization', frequency: 'monthly', time: '1st 08:00', enabled: true, lastRun: '2026-08-01', nextRun: '2026-09-01' },
  { id: '4', name: 'Risk Alert Digest', type: 'notification', frequency: 'daily', time: '17:00 UTC', enabled: false, lastRun: '2026-08-20', nextRun: '—' },
];

const TYPE_BADGES: Record<string, string> = { report: 'success', optimization: 'info', data_sync: 'warning', notification: 'danger' };

export default function ScheduleManager() {
  const [schedules, setSchedules] = useState<Schedule[]>(MOCK_SCHEDULES);
  const [showCreate, setShowCreate] = useState(false);
  const [newSchedule, setNewSchedule] = useState({ name: '', type: 'report' as Schedule['type'], frequency: 'weekly' as Schedule['frequency'], time: '' });

  const toggleSchedule = (id: string) => {
    setSchedules((prev) => prev.map((s) => s.id === id ? { ...s, enabled: !s.enabled } : s));
  };

  const createSchedule = () => {
    const schedule: Schedule = {
      id: String(Date.now()),
      ...newSchedule,
      enabled: true,
      nextRun: '2026-08-25' };
    setSchedules((prev) => [...prev, schedule]);
    setNewSchedule({ name: '', type: 'report', frequency: 'weekly', time: '' });
    setShowCreate(false);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white/80">Scheduled Tasks</h3>
        <Button variant="primary" size="sm" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? 'Cancel' : '+ New Schedule'}
        </Button>
      </div>

      {showCreate && (
        <Card className="p-4 space-y-3">
          <input
            type="text"
            placeholder="Schedule name"
            value={newSchedule.name}
            onChange={(e) => setNewSchedule((p) => ({ ...p, name: e.target.value }))}
            className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          />
          <div className="grid grid-cols-3 gap-2">
            <select
              value={newSchedule.type}
              onChange={(e) => setNewSchedule((p) => ({ ...p, type: e.target.value as Schedule['type'] }))}
              className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none"
            >
              <option value="report">Report</option>
              <option value="optimization">Optimization</option>
              <option value="data_sync">Data Sync</option>
              <option value="notification">Notification</option>
            </select>
            <select
              value={newSchedule.frequency}
              onChange={(e) => setNewSchedule((p) => ({ ...p, frequency: e.target.value as Schedule['frequency'] }))}
              className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="quarterly">Quarterly</option>
            </select>
            <input
              type="text"
              placeholder="Time (e.g., 09:00)"
              value={newSchedule.time}
              onChange={(e) => setNewSchedule((p) => ({ ...p, time: e.target.value }))}
              className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none"
            />
          </div>
          <Button variant="primary" size="sm" onClick={createSchedule} disabled={!newSchedule.name}>Create Schedule</Button>
        </Card>
      )}

      <div className="space-y-2">
        {schedules.map((s) => (
          <div key={s.id} className={`p-3 rounded-xl border transition-all ${s.enabled ? 'bg-white/[0.03] border-white/10' : 'bg-white/[0.01] border-white/5 opacity-50'}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <button onClick={() => toggleSchedule(s.id)} className={`w-10 h-5 rounded-full transition-colors ${s.enabled ? 'bg-blue-500' : 'bg-white/10'}`}>
                  <div className={`w-4 h-4 bg-white rounded-full shadow transition-transform ${s.enabled ? 'translate-x-5' : 'translate-x-0.5'}`} />
                </button>
                <div>
                  <span className="text-sm font-medium text-white">{s.name}</span>
                  <div className="flex items-center gap-2 mt-0.5">
                    <Badge variant={TYPE_BADGES[s.type] as 'success'}>{s.type}</Badge>
                    <span className="text-[10px] text-white/40">{s.frequency} • {s.time}</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-[10px] text-white/30">Next: {s.nextRun}</p>
                {s.lastRun && <p className="text-[10px] text-white/20">Last: {s.lastRun}</p>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
