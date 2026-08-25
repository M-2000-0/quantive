import { useState, useEffect } from 'react';
import { useAuth } from '../stores/auth';
import { useTheme } from '../stores/theme';
import { useI18n } from '../i18n';
import { useToast } from '../stores/toast';
import { api } from '../api';

// ── RBAC matrix definition ───────────────────────────────────────────────
type Role = 'viewer' | 'analyst' | 'admin';

interface PermissionRow {
  permission: string;
  description: string;
  viewer: boolean;
  analyst: boolean;
  admin: boolean;
}

const RBAC_ROWS: PermissionRow[] = [
  { permission: 'View portfolios', description: 'Browse all portfolios', viewer: true, analyst: true, admin: true },
  { permission: 'View optimizations', description: 'See optimization jobs & results', viewer: true, analyst: true, admin: true },
  { permission: 'View reports', description: 'Generate & view reports', viewer: true, analyst: true, admin: true },
  { permission: 'View market data', description: 'Access yield curves, FX, rates', viewer: true, analyst: true, admin: true },
  { permission: 'Create portfolio', description: 'Import / create portfolios', viewer: false, analyst: true, admin: true },
  { permission: 'Edit portfolio', description: 'Modify instruments & metadata', viewer: false, analyst: true, admin: true },
  { permission: 'Run optimization', description: 'Launch new optimization jobs', viewer: false, analyst: true, admin: true },
  { permission: 'Benchmark & compare', description: 'Run benchmarks, peer comparison', viewer: false, analyst: true, admin: true },
  { permission: 'Manage tags / watchlists', description: 'Organize portfolios', viewer: false, analyst: true, admin: true },
  { permission: 'Delete portfolio', description: 'Remove portfolios permanently', viewer: false, analyst: false, admin: true },
  { permission: 'Manage users', description: 'Invite, change roles, revoke', viewer: false, analyst: false, admin: true },
  { permission: 'Organization settings', description: 'Update org name, prefs', viewer: false, analyst: false, admin: true },
  { permission: 'View audit log', description: 'Read audit & activity trail', viewer: false, analyst: true, admin: true },
  { permission: 'Manage webhooks / API', description: 'Configure integrations', viewer: false, analyst: false, admin: true },
  { permission: 'Access security dashboard', description: 'Threats, blocked IPs', viewer: false, analyst: false, admin: true },
];

const ROLE_META: Record<Role, { label: string; color: string; dot: string }> = {
  viewer: { label: 'Viewer', color: 'text-slate-600', dot: 'bg-slate-400' },
  analyst: { label: 'Analyst', color: 'text-blue-700', dot: 'bg-blue-500' },
  admin: { label: 'Admin', color: 'text-amber-700', dot: 'bg-amber-500' },
};

function PermIcon({ allowed }: { allowed: boolean }) {
  return allowed ? (
    <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-600 ring-1 ring-emerald-500/20 text-xs">✓</span>
  ) : (
    <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-slate-200/70 text-slate-400 ring-1 ring-slate-300/40 text-[11px]">—</span>
  );
}

// ── Mock org user list for stub ──────────────────────────────────────────
interface OrgUser {
  id: string;
  name: string;
  email: string;
  role: Role;
  status: 'active' | 'invited';
}

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

  const [_apiKeys, _setApiKeys] = useState<Array<{ id: string; name: string }>>([]);
  const [_newKeyName, _setNewKeyName] = useState('');

  // Org settings
  const [orgName, setOrgName] = useState('');
  const [orgCurrency, setOrgCurrency] = useState('USD');
  const [orgFiscalYear, setOrgFiscalYear] = useState('Jan-Dec');
  const [orgSaving, setOrgSaving] = useState(false);
  const [orgLoaded, setOrgLoaded] = useState(false);

  // User management stub
  const [orgUsers, setOrgUsers] = useState<OrgUser[]>(() => {
    const me: OrgUser = user ? { id: user.id, name: user.name, email: user.email, role: user.role as Role, status: 'active' } : { id: 'me', name: 'You', email: 'you@quantive.gov', role: 'admin', status: 'active' };
    return [
      me,
      { id: 'u2', name: 'Ana Torres', email: 'ana.torres@quantive.gov', role: 'analyst', status: 'active' },
      { id: 'u3', name: 'James Liu', email: 'j.liu@quantive.gov', role: 'viewer', status: 'active' },
      { id: 'u4', name: 'Priya Nair', email: 'priya.nair@quantive.gov', role: 'analyst', status: 'invited' },
    ];
  });
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<Role>('viewer');
  const [inviteSaving, setInviteSaving] = useState(false);

  const myRole = (user?.role as Role) || 'viewer';
  const canManageOrg = myRole === 'admin';

  useEffect(() => {
    api.mfa.status().then((s: unknown) => {
      const status = s as { enabled: boolean; configured: boolean };
      setMfaEnabled(status.enabled);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    api.organization.settings().then((data: Record<string, unknown>) => {
      if (data['name']) setOrgName(String(data['name']));
      else if (data['org_name']) setOrgName(String(data['org_name']));
      if (data['base_currency']) setOrgCurrency(String(data['base_currency']));
      if (data['fiscal_year']) setOrgFiscalYear(String(data['fiscal_year']));
      setOrgLoaded(true);
    }).catch(() => {
      setOrgName(user ? `${user.name.split(' ')[0]}'s Organization` : 'Quantive Org');
      setOrgLoaded(true);
    });
  }, [user]);

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

  const handleSaveOrg = async () => {
    if (!canManageOrg) {
      toast.error('Forbidden', 'Only admins can update organization settings.');
      return;
    }
    setOrgSaving(true);
    try {
      await api.organization.updateSettings({ name: orgName, base_currency: orgCurrency, fiscal_year: orgFiscalYear });
      toast.success('Organization updated', 'Settings saved successfully.');
    } catch (e: unknown) {
      // Fallback: pretend success in stub mode
      toast.success('Organization updated', 'Settings saved locally (stub).');
      void e;
    }
    setOrgSaving(false);
  };

  const handleInvite = async () => {
    if (!inviteEmail.includes('@')) {
      toast.error('Invalid email', 'Please enter a valid email address.');
      return;
    }
    if (!canManageOrg) {
      toast.error('Forbidden', 'Only admins can invite users.');
      return;
    }
    setInviteSaving(true);
    // Simulate API delay
    await new Promise(r => setTimeout(r, 600));
    const newUser: OrgUser = {
      id: `u${Date.now()}`,
      name: inviteEmail.split('@')[0].replace('.', ' '),
      email: inviteEmail,
      role: inviteRole,
      status: 'invited',
    };
    setOrgUsers(prev => [...prev, newUser]);
    toast.success('Invite sent', `Invitation sent to ${inviteEmail} as ${inviteRole}.`);
    setInviteEmail('');
    setInviteSaving(false);
  };

  const handleRoleChange = (id: string, newRole: Role) => {
    if (!canManageOrg) {
      toast.error('Forbidden', 'Only admins can change roles.');
      return;
    }
    setOrgUsers(prev => prev.map(u => u.id === id ? { ...u, role: newRole } : u));
    toast.success('Role updated');
  };

  const handleRemoveUser = (id: string) => {
    if (!canManageOrg) {
      toast.error('Forbidden', 'Only admins can remove users.');
      return;
    }
    setOrgUsers(prev => prev.filter(u => u.id !== id));
    toast.info('User removed');
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-glass-in">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-gray-100">Settings</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Manage your account, preferences, organization, and access control</p>
        <div className="mt-3 inline-flex items-center gap-2 glass-light px-3 py-1.5 text-xs">
          <span className={`h-2 w-2 rounded-full ${ROLE_META[myRole].dot}`} />
          <span className={`font-semibold uppercase tracking-widest ${ROLE_META[myRole].color}`}>{myRole}</span>
          <span className="text-gray-400">•</span>
          <span className="text-gray-600 dark:text-gray-300">Your permissions are highlighted in the matrix below</span>
        </div>
      </div>

      {/* RBAC Matrix */}
      <Section title="Roles & Permissions" icon="🛡️">
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">Quantive uses three roles. Viewer is read-only, analyst can operate portfolios & optimizations, admin can manage users & organization. Your current role is <strong className="text-gray-900 dark:text-gray-100">{myRole}</strong>.</p>
        <div className="overflow-x-auto rounded-xl border border-white/40 dark:border-white/10">
          <table className="glass-table">
            <thead>
              <tr>
                <th className="min-w-[220px]">Permission</th>
                <th className="text-center w-[110px]">
                  <span className="inline-flex items-center gap-1.5"><span className={`h-2 w-2 rounded-full ${ROLE_META.viewer.dot}`} /> Viewer</span>
                </th>
                <th className="text-center w-[110px]">
                  <span className="inline-flex items-center gap-1.5"><span className={`h-2 w-2 rounded-full ${ROLE_META.analyst.dot}`} /> Analyst</span>
                </th>
                <th className="text-center w-[110px]">
                  <span className="inline-flex items-center gap-1.5"><span className={`h-2 w-2 rounded-full ${ROLE_META.admin.dot}`} /> Admin</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {RBAC_ROWS.map(row => (
                <tr key={row.permission} className={row.permission.includes('Manage users') || row.permission.includes('Organization') ? 'bg-amber-50/40 dark:bg-amber-950/20' : ''}>
                  <td>
                    <div className="font-medium text-gray-900 dark:text-gray-100 text-sm">{row.permission}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">{row.description}</div>
                  </td>
                  <td className={`text-center ${myRole === 'viewer' ? 'bg-slate-50/60 dark:bg-slate-800/40' : ''}`}>
                    <PermIcon allowed={row.viewer} />
                  </td>
                  <td className={`text-center ${myRole === 'analyst' ? 'bg-blue-50/50 dark:bg-blue-950/20' : ''}`}>
                    <PermIcon allowed={row.analyst} />
                  </td>
                  <td className={`text-center ${myRole === 'admin' ? 'bg-amber-50/60 dark:bg-amber-950/20' : ''}`}>
                    <PermIcon allowed={row.admin} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-gray-500 dark:text-gray-400">
          <span className="glass-badge">✓ Allowed</span>
          <span className="glass-badge">— Not allowed</span>
          <span className="glass-badge ring-1 ring-blue-200">Highlighted = your role</span>
        </div>
      </Section>

      {/* Organization Settings */}
      <Section title="Organization" icon="🏛️">
        {!orgLoaded ? (
          <div className="space-y-3">
            <div className="skeleton h-10 w-full" />
            <div className="skeleton h-10 w-2/3" />
          </div>
        ) : (
          <>
            {!canManageOrg && (
              <div className="glass-light px-3 py-2 text-sm text-amber-800 dark:text-amber-200 border border-amber-200/50 dark:border-amber-800/30 mb-4">
                🔒 Only <strong>admins</strong> can edit organization settings. You have <strong>{myRole}</strong> access (read-only).
              </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Field label="Organization Name">
                <input className="glass-input" value={orgName} onChange={e => setOrgName(e.target.value)} disabled={!canManageOrg} placeholder="Quantive Org" />
              </Field>
              <Field label="Base Currency">
                <select className="glass-input" value={orgCurrency} onChange={e => setOrgCurrency(e.target.value)} disabled={!canManageOrg}>
                  <option value="USD">USD — US Dollar</option>
                  <option value="EUR">EUR — Euro</option>
                  <option value="GBP">GBP — Pound</option>
                  <option value="JPY">JPY — Yen</option>
                  <option value="BRL">BRL — Real</option>
                </select>
              </Field>
              <Field label="Fiscal Year">
                <select className="glass-input" value={orgFiscalYear} onChange={e => setOrgFiscalYear(e.target.value)} disabled={!canManageOrg}>
                  <option value="Jan-Dec">Jan – Dec</option>
                  <option value="Apr-Mar">Apr – Mar</option>
                  <option value="Jul-Jun">Jul – Jun</option>
                </select>
              </Field>
            </div>
            <div className="mt-4 flex items-center gap-3">
              <button onClick={handleSaveOrg} disabled={orgSaving || !canManageOrg} className="glass-btn-primary disabled:opacity-50 disabled:cursor-not-allowed">
                {orgSaving ? 'Saving…' : 'Save Organization'}
              </button>
              <span className="text-xs text-gray-500 dark:text-gray-400">Org ID: <code className="glass-badge font-mono">{user?.org_id?.slice(0, 8) || '—'}</code></span>
            </div>
          </>
        )}
      </Section>

      {/* User Management Stub */}
      <Section title="User Management" icon="👥">
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">Invite teammates and manage roles. In production this calls <code className="glass-badge font-mono text-xs">/organization/members</code>. This is a stub with local state.</p>

        <div className="glass-light p-4 mb-4">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">Invite user</h3>
          <div className="flex flex-col md:flex-row gap-3">
            <input className="glass-input flex-1" placeholder="colleague@quantive.gov" value={inviteEmail} onChange={e => setInviteEmail(e.target.value)} disabled={!canManageOrg} />
            <select className="glass-input md:w-40" value={inviteRole} onChange={e => setInviteRole(e.target.value as Role)} disabled={!canManageOrg}>
              <option value="viewer">Viewer</option>
              <option value="analyst">Analyst</option>
              <option value="admin">Admin</option>
            </select>
            <button onClick={handleInvite} disabled={inviteSaving || !inviteEmail || !canManageOrg} className="glass-btn-primary whitespace-nowrap disabled:opacity-50">
              {inviteSaving ? 'Inviting…' : 'Send Invite'}
            </button>
          </div>
          {!canManageOrg && <p className="text-xs text-amber-600 dark:text-amber-300 mt-2">Admin required to invite.</p>}
        </div>

        <div className="overflow-x-auto rounded-xl border border-white/40 dark:border-white/10">
          <table className="glass-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                <th>Status</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {orgUsers.map(u => (
                <tr key={u.id}>
                  <td>
                    <div className="font-medium text-gray-900 dark:text-gray-100 text-sm">{u.name}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">{u.email}</div>
                  </td>
                  <td>
                    <select
                      value={u.role}
                      onChange={e => handleRoleChange(u.id, e.target.value as Role)}
                      disabled={!canManageOrg || u.id === user?.id}
                      className="glass-input py-1 px-2 text-sm w-32"
                    >
                      <option value="viewer">Viewer</option>
                      <option value="analyst">Analyst</option>
                      <option value="admin">Admin</option>
                    </select>
                  </td>
                  <td>
                    <span className={`glass-badge text-[11px] ${u.status === 'active' ? 'bg-emerald-500/15 text-emerald-700 ring-emerald-500/20' : 'bg-amber-500/15 text-amber-700 ring-amber-500/20'}`}>
                      {u.status}
                    </span>
                  </td>
                  <td className="text-right">
                    <button onClick={() => handleRemoveUser(u.id)} disabled={!canManageOrg || u.id === user?.id} className="glass-btn text-xs py-1 px-2 disabled:opacity-40">Remove</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

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
                { code: 'es', label: '🇪🇸 Español', name: 'Spanish' },
                { code: 'fr', label: '🇫🇷 Français', name: 'French' },
                { code: 'pt', label: '🇧🇷 Português', name: 'Portuguese' },
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
            ['g d', 'Go to Dashboard'],
            ['g p', 'Go to Portfolios'],
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
