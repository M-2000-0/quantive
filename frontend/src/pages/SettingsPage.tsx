import { useState } from 'react';

const TABS = [
  'Profile',
  'Security',
  'Appearance',
  'Notifications',
  'API Keys',
  'Organization',
  'Team',
  'Roles & Permissions',
  'Shortcuts',
] as const;

type Tab = (typeof TABS)[number];

export default function SettingsPage() {
  const [active, setActive] = useState<Tab>('Profile');

  return (
    <div>
      <h1>Settings</h1>
      <div role="tablist" aria-label="Settings sections">
        {TABS.map((tab) => (
          <button
            key={tab}
            role="tab"
            aria-selected={active === tab}
            type="button"
            onClick={() => setActive(tab)}
          >
            {tab}
          </button>
        ))}
      </div>
      <section role="tabpanel">
        {active === 'Profile' && (
          <div>
            <h2>Your Profile</h2>
            <label htmlFor="settings-name">Full Name</label>
            <input id="settings-name" type="text" />
          </div>
        )}
        {active === 'Security' && (
          <div>
            <h2>Security</h2>
            <button type="button">Change Password</button>
          </div>
        )}
        {active === 'Appearance' && (
          <div>
            <h2>Appearance</h2>
            <p>Theme</p>
            <p>Language</p>
          </div>
        )}
        {active === 'Notifications' && <h2>Notifications</h2>}
        {active === 'API Keys' && <h2>API Keys</h2>}
        {active === 'Organization' && <h2>Organization</h2>}
        {active === 'Team' && <h2>Team</h2>}
        {active === 'Roles & Permissions' && <h2>Roles & Permissions</h2>}
        {active === 'Shortcuts' && (
          <div>
            <h2>Shortcuts</h2>
            <p>⌘K / Ctrl+K</p>
            <p>Open command palette</p>
          </div>
        )}
      </section>
    </div>
  );
}
