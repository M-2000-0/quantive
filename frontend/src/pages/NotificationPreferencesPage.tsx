import { useState } from 'react';

const CATEGORIES = [
  'Price Alerts',
  'Maturity Alerts',
  'Credit Alerts',
  'Optimization Signals',
  'Consensus Alerts',
  'Market Events',
  'Weekly Report',
  'Monthly Peer Report',
];

function Toggle({ on, onClick, label }: { on: boolean; onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      onClick={onClick}
      className={`relative w-12 h-6 rounded-full transition-colors ${on ? 'bg-blue-600' : 'bg-slate-300'}`}
    >
      <span
        className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
          on ? 'translate-x-6' : 'translate-x-0.5'
        }`}
      />
    </button>
  );
}

export default function NotificationPreferencesPage() {
  const [volume, setVolume] = useState(70);
  const [emailMode, setEmailMode] = useState<'realtime' | 'digest'>('digest');
  const [pushEnabled, setPushEnabled] = useState(true);
  const [webhookEnabled, setWebhookEnabled] = useState(false);

  return (
    <div>
      <h1>Notification Preferences</h1>

      <section>
        <h2>Sound Alerts</h2>
        <label htmlFor="np-volume">Volume</label>
        <input
          id="np-volume"
          type="range"
          min={0}
          max={100}
          value={volume}
          onChange={(e) => setVolume(Number(e.target.value))}
        />
      </section>

      <section>
        <h2>Email Notifications</h2>
        <div>
          <button type="button" onClick={() => setEmailMode('realtime')}>
            Real-time
          </button>
          <button type="button" onClick={() => setEmailMode('digest')}>
            Digest
          </button>
        </div>
        {emailMode === 'digest' && (
          <div>
            <label htmlFor="np-delivery">Delivery Time</label>
            <input id="np-delivery" type="time" defaultValue="08:00" />
          </div>
        )}
      </section>

      <section>
        <h2>Push Notifications</h2>
        <Toggle on={pushEnabled} onClick={() => setPushEnabled((v) => !v)} label="Push notifications" />
      </section>

      <section>
        <h2>Alert Categories</h2>
        <ul>
          {CATEGORIES.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      </section>

      <section>
        <h2>Webhook Integration</h2>
        <Toggle on={webhookEnabled} onClick={() => setWebhookEnabled((v) => !v)} label="Webhook integration" />
        {webhookEnabled && (
          <input type="url" placeholder="https://hooks.slack.com/services/..." aria-label="Webhook URL" />
        )}
      </section>

      <button type="button">Save Preferences</button>
    </div>
  );
}
