import { useState, useEffect, useCallback } from 'react';

type ThemeName = 'light' | 'dark' | 'ocean' | 'forest' | 'sunset' | 'system';

interface ThemeConfig {
  name: ThemeName;
  label: string;
  icon: string;
  preview: { bg: string; surface: string; accent: string; text: string };
  vars: Record<string, string>;
}

const THEMES: ThemeConfig[] = [
  {
    name: 'light',
    label: 'Light',
    icon: '☀️',
    preview: { bg: '#f8fafc', surface: '#ffffff', accent: '#3b82f6', text: '#0f172a' },
    vars: {
      '--bg-primary': '#f8fafc',
      '--bg-surface': '#ffffff',
      '--bg-elevated': '#f1f5f9',
      '--text-primary': '#0f172a',
      '--text-secondary': '#64748b',
      '--accent-primary': '#3b82f6',
      '--accent-secondary': '#8b5cf6',
      '--border-color': 'rgba(0,0,0,0.08)',
      '--glass-bg': 'rgba(255,255,255,0.7)',
      '--glass-border': 'rgba(255,255,255,0.5)' } },
  {
    name: 'dark',
    label: 'Dark',
    icon: '🌙',
    preview: { bg: '#0f172a', surface: '#1e293b', accent: '#60a5fa', text: '#f1f5f9' },
    vars: {
      '--bg-primary': '#0f172a',
      '--bg-surface': '#1e293b',
      '--bg-elevated': '#334155',
      '--text-primary': '#f1f5f9',
      '--text-secondary': '#94a3b8',
      '--accent-primary': '#60a5fa',
      '--accent-secondary': '#a78bfa',
      '--border-color': 'rgba(255,255,255,0.1)',
      '--glass-bg': 'rgba(30,41,59,0.7)',
      '--glass-border': 'rgba(255,255,255,0.08)' } },
  {
    name: 'ocean',
    label: 'Ocean',
    icon: '🌊',
    preview: { bg: '#0c1929', surface: '#132f4c', accent: '#00b4d8', text: '#e0f2fe' },
    vars: {
      '--bg-primary': '#0c1929',
      '--bg-surface': '#132f4c',
      '--bg-elevated': '#1a3a5c',
      '--text-primary': '#e0f2fe',
      '--text-secondary': '#7dd3fc',
      '--accent-primary': '#00b4d8',
      '--accent-secondary': '#06b6d4',
      '--border-color': 'rgba(0,180,216,0.15)',
      '--glass-bg': 'rgba(19,47,76,0.7)',
      '--glass-border': 'rgba(0,180,216,0.12)' } },
  {
    name: 'forest',
    label: 'Forest',
    icon: '🌲',
    preview: { bg: '#0a1a0f', surface: '#132e1a', accent: '#22c55e', text: '#dcfce7' },
    vars: {
      '--bg-primary': '#0a1a0f',
      '--bg-surface': '#132e1a',
      '--bg-elevated': '#1a3d22',
      '--text-primary': '#dcfce7',
      '--text-secondary': '#86efac',
      '--accent-primary': '#22c55e',
      '--accent-secondary': '#10b981',
      '--border-color': 'rgba(34,197,94,0.15)',
      '--glass-bg': 'rgba(19,46,26,0.7)',
      '--glass-border': 'rgba(34,197,94,0.12)' } },
  {
    name: 'sunset',
    label: 'Sunset',
    icon: '🌅',
    preview: { bg: '#1a0a0a', surface: '#2d1515', accent: '#f97316', text: '#fef3c7' },
    vars: {
      '--bg-primary': '#1a0a0a',
      '--bg-surface': '#2d1515',
      '--bg-elevated': '#3d1f1f',
      '--text-primary': '#fef3c7',
      '--text-secondary': '#fbbf24',
      '--accent-primary': '#f97316',
      '--accent-secondary': '#ef4444',
      '--border-color': 'rgba(249,115,22,0.15)',
      '--glass-bg': 'rgba(45,21,21,0.7)',
      '--glass-border': 'rgba(249,115,22,0.12)' } },
  {
    name: 'system',
    label: 'System',
    icon: '💻',
    preview: { bg: '#334155', surface: '#475569', accent: '#3b82f6', text: '#334155' },
    vars: {} },
];

interface ThemeTransitionProps {
  currentTheme?: ThemeName;
  onThemeChange?: (theme: ThemeName) => void;
}

export default function ThemeTransition({ currentTheme: controlledTheme, onThemeChange }: ThemeTransitionProps) {
  const [selectedTheme, setSelectedTheme] = useState<ThemeName>(controlledTheme || 'light');
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [showPicker, setShowPicker] = useState(false);

  const applyTheme = useCallback((theme: ThemeConfig) => {
    if (theme.name === 'system') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      const resolved = prefersDark ? THEMES.find(t => t.name === 'dark')! : THEMES.find(t => t.name === 'light')!;
      applyTheme(resolved);
      return;
    }

    setIsTransitioning(true);

    // Apply CSS variables with transition
    const root = document.documentElement;
    Object.entries(theme.vars).forEach(([key, value]) => {
      root.style.setProperty(key, value);
    });

    // Store preference
    localStorage.setItem('quantive_theme', theme.name);

    setTimeout(() => setIsTransitioning(false), 500);
  }, []);

  const handleThemeSelect = useCallback((theme: ThemeConfig) => {
    setSelectedTheme(theme.name);
    applyTheme(theme);
    onThemeChange?.(theme.name);
    setShowPicker(false);
  }, [applyTheme, onThemeChange]);

  // Load saved theme on mount
  useEffect(() => {
    const saved = localStorage.getItem('quantive_theme') as ThemeName | null;
    if (saved) {
      const theme = THEMES.find(t => t.name === saved);
      if (theme) {
        setSelectedTheme(saved);
        applyTheme(theme);
      }
    }
  }, [applyTheme]);

  const current = THEMES.find(t => t.name === selectedTheme) || THEMES[0];

  return (
    <div className="relative">
      {/* Theme trigger button */}
      <button
        onClick={() => setShowPicker(!showPicker)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-xl glass border border-white/40 hover:border-white/60 text-sm font-medium text-slate-700 hover:bg-white/40 transition-all backdrop-blur-md"
      >
        <span>{current.icon}</span>
        <span className="hidden sm:inline">{current.label}</span>
        <svg className={`h-3.5 w-3.5 text-slate-400 transition-transform ${showPicker ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {/* Transition overlay */}
      {isTransitioning && (
        <div className="fixed inset-0 z-[9999] pointer-events-none">
          <div className="absolute inset-0 bg-white/20 backdrop-blur-sm animate-pulse" style={{ animation: 'fadeOut 0.5s ease-out' }} />
        </div>
      )}

      {/* Theme picker dropdown */}
      {showPicker && (
        <div className="absolute right-0 top-full mt-2 w-72 glass-strong rounded-2xl shadow-2xl border border-white/30 z-50 overflow-hidden animate-glass-in">
          <div className="px-4 py-3 border-b border-white/20">
            <h3 className="text-sm font-bold text-slate-900">Choose Theme</h3>
            <p className="text-[11px] text-slate-500 mt-0.5">Select a color scheme for the interface</p>
          </div>

          <div className="p-3 grid grid-cols-2 gap-2">
            {THEMES.map(theme => (
              <button
                key={theme.name}
                onClick={() => handleThemeSelect(theme)}
                className={`relative p-3 rounded-xl border-2 transition-all text-left ${
                  selectedTheme === theme.name
                    ? 'border-blue-500 bg-blue-50/50 shadow-md'
                    : 'border-white/30 hover:border-white/50 hover:bg-white/30'
                }`}
              >
                {/* Preview swatches */}
                <div className="flex gap-1 mb-2">
                  <div className="w-6 h-6 rounded-lg border border-white/20" style={{ background: theme.preview.bg }} />
                  <div className="w-6 h-6 rounded-lg border border-white/20" style={{ background: theme.preview.surface }} />
                  <div className="w-6 h-6 rounded-lg border border-white/20" style={{ background: theme.preview.accent }} />
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-base">{theme.icon}</span>
                  <span className="text-xs font-semibold text-slate-700">{theme.label}</span>
                </div>
                {selectedTheme === theme.name && (
                  <div className="absolute top-2 right-2 w-4 h-4 rounded-full bg-blue-500 flex items-center justify-center">
                    <svg className="h-2.5 w-2.5 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  </div>
                )}
              </button>
            ))}
          </div>

          <div className="px-4 py-2 border-t border-white/20 text-center">
            <p className="text-[10px] text-slate-400">Changes apply instantly with smooth transition</p>
          </div>
        </div>
      )}
    </div>
  );
}
