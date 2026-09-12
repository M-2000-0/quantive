import { useState } from 'react';
import { Card } from './ui';
import { Badge } from './ui';
import { Button } from './ui';

interface Session {
  id: string;
  device: string;
  browser: string;
  ip: string;
  location: string;
  lastActive: string;
  createdAt: string;
  isCurrent: boolean;
}

const MOCK_SESSIONS: Session[] = [
  { id: '1', device: 'MacBook Pro', browser: 'Chrome 130', ip: '192.168.1.42', location: 'Washington, DC', lastActive: 'Now', createdAt: '3 days ago', isCurrent: true },
  { id: '2', device: 'iPhone 15', browser: 'Safari Mobile', ip: '10.0.0.15', location: 'Washington, DC', lastActive: '2h ago', createdAt: '1 week ago', isCurrent: false },
  { id: '3', device: 'Windows Desktop', browser: 'Firefox 128', ip: '172.16.0.88', location: 'New York, NY', lastActive: '2 days ago', createdAt: '2 weeks ago', isCurrent: false },
];

export default function SessionManager() {
  const [sessions, setSessions] = useState<Session[]>(MOCK_SESSIONS);

  const revokeSession = (id: string) => {
    setSessions((prev) => prev.filter((s) => s.id !== id));
  };

  const revokeAll = () => {
    setSessions((prev) => prev.filter((s) => s.isCurrent));
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-white">Active Sessions</h3>
        <Button variant="ghost" size="sm" onClick={revokeAll}>Revoke All Others</Button>
      </div>

      <div className="space-y-2">
        {sessions.map((s) => (
          <Card key={s.id} className={`p-4 ${s.isCurrent ? 'ring-1 ring-blue-500/30' : ''}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="text-2xl">
                  {s.device.includes('iPhone') ? '📱' : s.device.includes('Mac') ? '💻' : '🖥️'}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white">{s.device}</span>
                    {s.isCurrent && <Badge variant="success">Current</Badge>}
                  </div>
                  <p className="text-xs text-white/40">{s.browser} • {s.ip}</p>
                  <p className="text-[10px] text-white/30">{s.location}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-xs text-white/50">Last active: {s.lastActive}</p>
                <p className="text-[10px] text-white/30">Since: {s.createdAt}</p>
                {!s.isCurrent && (
                  <button onClick={() => revokeSession(s.id)} className="text-[10px] text-red-400/60 hover:text-red-400 mt-1">
                    Revoke
                  </button>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
