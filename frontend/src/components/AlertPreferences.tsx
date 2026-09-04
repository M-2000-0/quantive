import { useState } from 'react';
import type { AlertPreference } from '../lib/purchaseData';

const CHANNEL_ICONS: Record<string, string> = {
  email: '📧',
  in_app: '🔔',
  sms: '📱',
  webhook: '🔗' };

const CATEGORY_COLORS: Record<string, string> = {
  'Price Movements': 'from-blue-500 to-cyan-500',
  'Credit Events': 'from-amber-500 to-orange-500',
  'Market Conditions': 'from-purple-500 to-pink-500',
  'Opportunities': 'from-emerald-500 to-teal-500',
  'Portfolio Health': 'from-rose-500 to-red-500' };

export default function AlertPreferences() {
  const [preferences, setPreferences] = useState([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleAlert = (id: string) => {
    setPreferences((prev) => prev.map((p) => (p.id === id ? { ...p, enabled: !p.enabled } : p)));
  };

  const toggleChannel = (id: string, channel: AlertPreference['channels'][number]) => {
    setPreferences((prev) =>
      prev.map((p) =>
        p.id === id
          ? {
              ...p,
              channels: p.channels.includes(channel)
                ? p.channels.filter((c) => c !== channel)
                : [...p.channels, channel] }
          : p
      )
    );
  };

  const categories = Array.from(new Set(preferences.map((p) => p.category)));
  const enabledCount = preferences.filter((p) => p.enabled).length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Alert Preferences</h3>
          <p className="text-sm text-slate-500">
            Configure when and how you receive notifications
          </p>
        </div>
        <div className="glass px-3 py-1.5 rounded-xl text-xs font-medium text-slate-600">
          {enabledCount}/{preferences.length} alerts active
        </div>
      </div>

      {categories.map((category) => (
        <div key={category} className="space-y-2">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full bg-gradient-to-r ${CATEGORY_COLORS[category] || 'from-slate-400 to-slate-500'}`} />
            <h4 className="text-sm font-semibold text-slate-700">{category}</h4>
          </div>

          {preferences
            .filter((p) => p.category === category)
            .map((pref) => (
              <div
                key={pref.id}
                className={`glass rounded-xl p-4 transition-all ${
                  pref.enabled ? 'ring-1 ring-blue-400/20' : 'opacity-70'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 flex-1">
                    <button
                      onClick={() => toggleAlert(pref.id)}
                      className={`relative w-10 h-5 rounded-full transition-colors ${
                        pref.enabled ? 'bg-blue-600' : 'bg-slate-300'
                      }`}
                    >
                      <div
                        className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                          pref.enabled ? 'translate-x-5' : 'translate-x-0.5'
                        }`}
                      />
                    </button>
                    <div className="flex-1">
                      <div className="font-medium text-sm text-slate-900">{pref.label}</div>
                      <div className="text-xs text-slate-500">{pref.description}</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {pref.threshold && (
                      <span className="text-[10px] font-mono text-slate-400 bg-slate-50 px-2 py-0.5 rounded-lg">
                        {pref.threshold}
                      </span>
                    )}
                    <button
                      onClick={() => setExpandedId(expandedId === pref.id ? null : pref.id)}
                      className="text-xs text-slate-400 hover:text-slate-600 transition-colors"
                    >
                      {expandedId === pref.id ? '▲' : '▼'}
                    </button>
                  </div>
                </div>

                {/* Channel Selection */}
                {expandedId === pref.id && (
                  <div className="mt-3 pt-3 border-t border-white/20">
                    <div className="text-xs text-slate-500 mb-2">Notification channels:</div>
                    <div className="flex gap-2">
                      {(['email', 'in_app', 'sms', 'webhook'] as const).map((channel) => (
                        <button
                          key={channel}
                          onClick={() => toggleChannel(pref.id, channel)}
                          className={`flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-xl transition-all ${
                            pref.channels.includes(channel)
                              ? 'bg-blue-600/14 text-blue-700 ring-1 ring-blue-400/20'
                              : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                          }`}
                        >
                          <span>{CHANNEL_ICONS[channel]}</span>
                          <span className="capitalize">{channel.replace('_', ' ')}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
        </div>
      ))}

      <div className="glass rounded-xl p-4 text-xs text-slate-500">
        <strong>Note:</strong> SMS alerts are available on Pro plans only. Webhook alerts require a valid endpoint URL in your notification settings.
      </div>
    </div>
  );
}
