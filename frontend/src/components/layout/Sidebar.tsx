import { useState, useCallback } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Activity, AlertTriangle, BarChart, BarChart3, BookOpenCheck, BrainCircuit, Bug, Building2, Calculator, Calendar, CheckCircle2, CheckSquare, ChevronDown, CircleAlert, ClipboardList, Coins, Cpu, DollarSign, Eye, FileSearch, FileText, Flag, GitBranch, Heart, HelpCircle, Landmark, Layers, Lightbulb, LineChart, Lock, Mail, MessageCircle, Monitor, Newspaper, Radio, Scale, Settings, ShieldAlert, ShieldCheck, Target, Ticket, TrendingUp, Users, Workflow, Zap } from 'lucide-react';
import LanguageSwitcher from '../LanguageSwitcher';

interface SidebarProps {
  collapsed: boolean;
  onClose: () => void;
  currentPath: string;
}

interface NavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
}

interface NavSection {
  id: string;
  label: string;
  items: NavItem[];
}

const DECISION_SECTIONS: NavSection[] = [
  {
    id: 'assess',
    label: 'Assess',
    items: [
      { label: 'Dashboard', path: '/dashboard', icon: <BarChart3 className="h-4 w-4" /> },
      { label: 'Portfolio', path: '/portfolios', icon: <Building2 className="h-4 w-4" /> },
      { label: 'Market Data', path: '/market', icon: <LineChart className="h-4 w-4" /> },
      { label: 'Risk Overview', path: '/risk', icon: <AlertTriangle className="h-4 w-4" /> },
      { label: 'Early Warning', path: '/early-warning', icon: <Radio className="h-4 w-4" /> },
      { label: 'Sovereign Health', path: '/sovereign-health', icon: <Heart className="h-4 w-4" /> },
      { label: 'Consolidated Debt', path: '/consolidated', icon: <Layers className="h-4 w-4" /> },
    ],
  },
  {
    id: 'simulate',
    label: 'Simulate',
    items: [
      { label: 'New Optimization', path: '/optimizations/new', icon: <GitBranch className="h-4 w-4" /> },
      { label: 'What-If Analysis', path: '/whatif', icon: <Lightbulb className="h-4 w-4" /> },
      { label: 'Digital Twin', path: '/digital-twin', icon: <Cpu className="h-4 w-4" /> },
      { label: 'Stress Test', path: '/black-swan', icon: <Eye className="h-4 w-4" /> },
      { label: 'Policy Impact', path: '/policy-impact', icon: <Scale className="h-4 w-4" /> },
      { label: 'Crisis Mode', path: '/crisis', icon: <CircleAlert className="h-4 w-4" /> },
      { label: 'Pareto Frontier', path: '/pareto', icon: <Target className="h-4 w-4" /> },
      { label: 'Scenario Compare', path: '/scenario-compare', icon: <GitBranch className="h-4 w-4" /> },
    ],
  },
  {
    id: 'decide',
    label: 'Decide',
    items: [
      { label: 'AI Copilot', path: '/copilot', icon: <BrainCircuit className="h-4 w-4" /> },
      { label: 'Explainability', path: '/explain-engine', icon: <FileSearch className="h-4 w-4" /> },
      { label: 'ROI Engine', path: '/roi-engine', icon: <Coins className="h-4 w-4" /> },
      { label: 'Rating Agency', path: '/rating-agency', icon: <Flag className="h-4 w-4" /> },
      { label: 'Issuance Planner', path: '/issuance-planner', icon: <ClipboardList className="h-4 w-4" /> },
    ],
  },
  {
    id: 'approve',
    label: 'Approve',
    items: [
      { label: 'Approval Workflow', path: '/approvals', icon: <Workflow className="h-4 w-4" /> },
      { label: 'Decision Vault', path: '/decision-vault', icon: <Lock className="h-4 w-4" /> },
      { label: 'Minister Brief', path: '/minister', icon: <Landmark className="h-4 w-4" /> },
      { label: 'Compliance', path: '/compliance', icon: <CheckCircle2 className="h-4 w-4" /> },
      { label: 'Fiscal Rules', path: '/fiscal-rules', icon: <Scale className="h-4 w-4" /> },
      { label: 'Audit Trail', path: '/immutable-audit', icon: <BookOpenCheck className="h-4 w-4" /> },
    ],
  },
  {
    id: 'monitor',
    label: 'Monitor',
    items: [
      { label: 'Execution Log', path: '/executions', icon: <ClipboardList className="h-4 w-4" /> },
      { label: 'Fraud Detection', path: '/fraud-detection', icon: <ShieldAlert className="h-4 w-4" /> },
      { label: 'Reports', path: '/reports', icon: <FileText className="h-4 w-4" /> },
      { label: 'Security', path: '/security', icon: <ShieldCheck className="h-4 w-4" /> },
      { label: 'SOC 2 Dashboard', path: '/soc-dashboard', icon: <ShieldCheck className="h-4 w-4" /> },
      { label: 'Settings', path: '/settings', icon: <Settings className="h-4 w-4" /> },
    ],
  },
  {
    id: 'ops',
    label: 'Operations',
    items: [
      { label: 'News Feed', path: '/news', icon: <Newspaper className="h-4 w-4" /> },
      { label: 'Tasks', path: '/tasks', icon: <CheckSquare className="h-4 w-4" /> },
      { label: 'Meetings', path: '/meetings', icon: <Calendar className="h-4 w-4" /> },
      { label: 'Help Center', path: '/help', icon: <HelpCircle className="h-4 w-4" /> },
      { label: 'Support Tickets', path: '/tickets', icon: <Ticket className="h-4 w-4" /> },
      { label: 'Bug Reports', path: '/bugs', icon: <Bug className="h-4 w-4" /> },
    ],
  },
  {
    id: 'business',
    label: 'Business',
    items: [
      { label: 'Revenue', path: '/revenue', icon: <DollarSign className="h-4 w-4" /> },
      { label: 'Pipeline', path: '/pipeline', icon: <TrendingUp className="h-4 w-4" /> },
      { label: 'Campaigns', path: '/campaigns', icon: <Mail className="h-4 w-4" /> },
    ],
  },
];

function isActive(path: string, currentPath: string): boolean {
  if (path === '/dashboard') return currentPath === '/dashboard';
  return currentPath.startsWith(path);
}

export default function Sidebar({ collapsed, onClose, currentPath }: SidebarProps) {
  const [openSection, setOpenSection] = useState<string | null>(() => {
    for (const section of DECISION_SECTIONS) {
      if (section.items.some(item => isActive(item.path, currentPath))) {
        return section.id;
      }
    }
    return 'assess';
  });

  const toggleSection = useCallback((id: string) => {
    setOpenSection(prev => prev === id ? null : id);
  }, []);

  return (
    <>
      {!collapsed && (
        <div className="fixed inset-0 z-40 bg-black/40 lg:hidden" onClick={onClose} />
      )}

      <aside
        className={`
          fixed inset-y-0 left-0 z-50 flex w-[236px] flex-col
          transition-transform duration-200 ease-out
          lg:static lg:translate-x-0
          ${collapsed ? '-translate-x-full' : 'translate-x-0'}
        `}
        style={{
          background: 'var(--sidebar-bg)',
          borderRight: '1px solid var(--border)',
          backdropFilter: 'blur(16px) saturate(1.2)',
          WebkitBackdropFilter: 'blur(16px) saturate(1.2)',
        }}
      >
        {/* Logo */}
        <div
          className="flex items-center gap-3"
          style={{ padding: '20px 16px 16px', borderBottom: '1px solid var(--border)' }}
        >
          <div
            className="flex items-center justify-center flex-shrink-0"
            style={{
              width: 30,
              height: 30,
              borderRadius: 8,
              background: 'var(--accent)',
              color: '#0a0a0b',
              fontSize: 13,
              fontWeight: 800,
              boxShadow: '0 0 12px rgba(200, 169, 81, 0.2), inset 0 1px 0 rgba(255,255,255,0.15)',
            }}
          >
            Q
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text)' }}>
              Quantive
            </div>
            <div style={{ fontSize: 9, color: 'var(--text3)', letterSpacing: '0.1em', textTransform: 'uppercase', marginTop: 1, fontWeight: 500 }}>
              Sovereign Finance
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto" style={{ padding: '10px 8px' }}>
          {/* Home link */}
          <Link
            to="/dashboard"
            onClick={onClose}
            className="flex items-center gap-2.5"
            style={{
              padding: '8.5px 11px',
              borderRadius: 'var(--radius)',
              cursor: 'pointer',
              color: currentPath === '/dashboard' ? 'var(--active-text)' : 'var(--text2)',
              fontSize: 13,
              fontWeight: currentPath === '/dashboard' ? 600 : 500,
              background: currentPath === '/dashboard' ? 'linear-gradient(90deg, var(--hover2), transparent)' : 'transparent',
              position: 'relative',
              marginBottom: 1,
              transition: 'all 0.14s ease',
            }}
          >
            <BarChart3 style={{ width: 16, height: 16, opacity: currentPath === '/dashboard' ? 1 : 0.75 }} />
            Home
          </Link>

          {/* Sections */}
          {DECISION_SECTIONS.map(section => {
            const isOpen = openSection === section.id;
            const hasActive = section.items.some(item => isActive(item.path, currentPath));

            return (
              <div key={section.id}>
                {/* Section header — ALL CAPS */}
                <div
                  style={{
                    fontSize: 10,
                    color: 'var(--text3)',
                    textTransform: 'uppercase',
                    letterSpacing: '1px',
                    padding: '14px 12px 6px',
                    fontWeight: 600,
                  }}
                >
                  {section.label}
                </div>

                {/* Section items */}
                <div>
                  {section.items.map(item => {
                    const active = isActive(item.path, currentPath);
                    return (
                      <Link
                        key={item.path}
                        to={item.path}
                        onClick={onClose}
                        className="flex items-center gap-2.5"
                        style={{
                          padding: '8.5px 11px',
                          borderRadius: 'var(--radius)',
                          cursor: 'pointer',
                          color: active ? 'var(--active-text)' : 'var(--text2)',
                          fontSize: 13,
                          fontWeight: active ? 600 : 500,
                          background: active ? 'linear-gradient(90deg, var(--hover2), transparent)' : 'transparent',
                          position: 'relative',
                          marginBottom: 1,
                          transition: 'all 0.14s ease',
                        }}
                      >
                        {/* Active left border glow */}
                        {active && (
                          <div
                            style={{
                              position: 'absolute',
                              left: 0,
                              top: '22%',
                              height: '56%',
                              width: 2.5,
                              borderRadius: 3,
                              background: 'var(--accent)',
                              boxShadow: '0 0 10px rgba(200, 169, 81, 0.4)',
                            }}
                          />
                        )}
                        <span style={{ width: 16, height: 16, opacity: active ? 1 : 0.65, color: active ? 'var(--accent)' : undefined }}>
                          {item.icon}
                        </span>
                        <span style={{ flex: 1 }} className="truncate">{item.label}</span>
                      </Link>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </nav>

        {/* Footer */}
        <div style={{ padding: 12, borderTop: '1px solid var(--border)' }}>
          <div
            className="flex items-center"
            style={{
              fontSize: 11,
              color: 'var(--text3)',
              letterSpacing: '0.4px',
              padding: '6px 10px',
              gap: 7,
            }}
          >
            <span
              className="local-dot"
              style={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                background: 'var(--green)',
                boxShadow: '0 0 8px rgba(34,197,94,0.8)',
                flexShrink: 0,
              }}
            />
            <span>Local-first · Online</span>
          </div>
          <div className="mt-1"><LanguageSwitcher /></div>
        </div>
      </aside>
    </>
  );
}
