import { useState, useEffect } from 'react';
import { useAuth } from '../stores/auth';
import { useTheme } from '../stores/theme';
import { useI18n } from '../i18n';
import { useToast } from '../stores/toast';
import { api } from '../api';

export default function SettingsPage() {
  const { user } = useAuth();
  const { theme, setTheme } = useTheme();
  const { locale, setLocale } = useI18n();
  const toast = useToast();

  const [name, setName] = useState(user?.name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [saving, setSaving] = useState(false);

  // MFA state
  const [mfaEnabled, setMfaEnabled] = useState(false);
  const [mfaQr, setMfaQr] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  const [mfaBackupCodes, setMfaBackupCodes] = useState<string[]>([]);

  // API Keys state (placeholder for future implementation)
  const [_apiKeys, _setApiKeys] = useState<Array<{ id: string; name: string }>>([]);
  const [_newKeyName, _setNewKeyName] = useState('');

  useEffect(() => {
    api.mfa.status().then((s: unknown) => {
      const status = s as { enabled: boolean; configured: boolean };
      setMfaEnabled(status.enabled);
    }).catch(() => {});
  }, []);

  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      await api.auth.updateMe({ name, email });
      toast.success('Profile updated', 'Your name and email have been saved.');
    } catch (e: unknown) {
      toast.error('Update failed', e instanceof Error ? e.message : 'Unknown error');
    }
    setSaving(false);
  };

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    if (newPassword.length < 8) {
      toast.error('Password too short', 'Must be at least 8 characters.');
      return;
    }
    setSaving(true);
    try {
      await api.auth.changePassword({ current_password: currentPassword, new_password: newPassword });
      toast.success('Password changed', 'Your password has been updated.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (e: unknown) {
      toast.error('Password change failed', e instanceof Error ? e.message : 'Unknown error');
    }
    setSaving(false);
  };

  const handleSetupMfa = async () => {
    try {
      const result = await api.mfa.setup();
      setMfaQr(result.qr_code_svg);
    } catch (e: unknown) {
      toast.error('MFA setup failed', e instanceof Error ? e.message : 'Unknown error');
    }
  };

  const handleEnableMfa = async () => {
    try {
      const result = await api.mfa.enable(mfaCode);
      setMfaEnabled(true);
      setMfaBackupCodes(result.backup_codes);
      toast.success('MFA enabled', 'Two-factor authentication is now active.');
    } catch (e: unknown) {
      toast.error('MFA enable failed', e instanceof Error ? e.message : 'Unknown error');
    }
  };

  const handleDisableMfa = async () => {
    try {
      await api.mfa.disable(mfaCode);
      setMfaEnabled(false);
      toast.success('MFA disabled');
    } catch (e: unknown) {
      toast.error('MFA disable failed', e instanceof Error ? e.message : 'Unknown error');
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-glass-in">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Settings</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Manage your account, preferences, and security</p>
      </div>

      {/* Profile */}
      <Section title="Profile" icon="👤">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field label="Full Name">
            <input className="glass-input" value={name} onChange={e => setName(e.target.value)} />
          </Field>
          <Field label="Email">
            <input className="glass-input" type="email" value={email} onChange={e => setEmail(e.target.value)} />
          </Field>
        </div>
        <button onClick={handleSaveProfile} disabled={saving} className="glass-btn-primary mt-4">
          {saving ? 'Saving...' : 'Save Profile'}
        </button>
      </Section>

      {/* Password */}
      <Section title="Change Password" icon="🔐">
        <div className="space-y-3 max-w-md">
          <Field label="Current Password">
            <input className="glass-input" type="password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} />
          </Field>
          <Field label="New Password">
            <input className="glass-input" type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} />
          </Field>
          <Field label="Confirm New Password">
            <input className="glass-input" type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} />
          </Field>
        </div>
        <button onClick={handleChangePassword} disabled={saving || !currentPassword} className="glass-btn-primary mt-4">
          Change Password
        </button>
      </Section>

      {/* Appearance */}
      <Section title="Appearance" icon="🎨">
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">Theme</label>
            <div className="flex gap-3">
              {(['light', 'dark', 'system'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setTheme(t)}
                  className={`glass-btn capitalize ${theme === t ? 'ring-2 ring-blue-400 !bg-blue-50 dark:!bg-blue-950/50' : ''}`}
                >
                  {t === 'light' ? '☀️ Light' : t === 'dark' ? '🌙 Dark' : '💻 System'}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">Language</label>
            <div className="flex gap-3">
              {([
                { code: 'en', label: '🇬🇧 English', name: 'English' },
                { code: 'es', label: '🇪🇸 Espanol', name: 'Spanish' },
                { code: 'fr', label: '🇫🇷 Francais', name: 'French' },
                { code: 'pt', label: '🇧🇷 Portugues', name: 'Portuguese' },
              ]).map(l => (
                <button
                  key={l.code}
                  onClick={() => setLocale(l.code as 'en' | 'es' | 'fr' | 'pt')}
                  className={`glass-btn ${locale === l.code ? 'ring-2 ring-blue-400 !bg-blue-50 dark:!bg-blue-950/50' : ''}`}
                >
                  {l.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Section>

      {/* Two-Factor Auth */}
      <Section title="Two-Factor Authentication" icon="🛡️">
        <div className="flex items-center gap-3 mb-4">
          <div className={`w-3 h-3 rounded-full ${mfaEnabled ? 'bg-green-500' : 'bg-gray-300'}`} />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {mfaEnabled ? 'MFA is enabled' : 'MFA is not enabled'}
          </span>
        </div>

        {!mfaEnabled ? (
          <div className="space-y-3">
            <button onClick={handleSetupMfa} className="glass-btn">Set up MFA</button>
            {mfaQr && (
              <div className="glass p-4 inline-block">
                <div dangerouslySetInnerHTML={{ __html: mfaQr }} className="w-48 h-48" />
                <div className="mt-3">
                  <input className="glass-input" placeholder="Enter 6-digit code" value={mfaCode} onChange={e => setMfaCode(e.target.value)} maxLength={6} />
                  <button onClick={handleEnableMfa} className="glass-btn-primary mt-2" disabled={mfaCode.length < 6}>Enable MFA</button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            <input className="glass-input max-w-xs" placeholder="Enter code to disable" value={mfaCode} onChange={e => setMfaCode(e.target.value)} maxLength={6} />
            <button onClick={handleDisableMfa} className="glass-btn text-red-600 border-red-200" disabled={mfaCode.length < 6}>Disable MFA</button>
          </div>
        )}

        {mfaBackupCodes.length > 0 && (
          <div className="glass p-4 mt-4">
            <p className="text-sm font-semibold text-yellow-700 dark:text-yellow-300 mb-2">Backup Codes (save these!):</p>
            <div className="grid grid-cols-2 gap-1 font-mono text-sm">
              {mfaBackupCodes.map(c => <code key={c} className="text-gray-700 dark:text-gray-300">{c}</code>)}
            </div>
          </div>
        )}
      </Section>

      {/* Keyboard Shortcuts */}
      <Section title="Keyboard Shortcuts" icon="⌨️">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
          {[
            ['⌘K / Ctrl+K', 'Open command palette'],
            ['⌘/Ctrl + /', 'Toggle shortcuts help'],
          ].map(([key, desc]) => (
            <div key={key} className="flex items-center gap-3 py-1.5">
              <kbd className="glass-badge font-mono text-xs">{key}</kbd>
              <span className="text-gray-600 dark:text-gray-400">{desc}</span>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}

function Section({ title, icon, children }: { title: string; icon: string; children: React.ReactNode }) {
  return (
    <div className="glass p-6">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
        <span>{icon}</span> {title}
      </h2>
      {children}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{label}</label>
      {children}
    </div>
  );
}
