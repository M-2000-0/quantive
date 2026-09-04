// ── Premium Empty States ──────────────────────────────────────────────
// Every empty state should guide the user to action.
// Never show "No Data" — always explain what's missing and how to fix it.

import { useNavigate } from 'react-router-dom';
import { Briefcase, TrendingUp, Shield, FileText, Upload, Play } from 'lucide-react';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick?: () => void;
    href?: string;
  };
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  const navigate = useNavigate();

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '48px 24px',
      textAlign: 'center',
      maxWidth: 400,
      margin: '0 auto',
    }}>
      {icon && (
        <div style={{
          width: 48,
          height: 48,
          borderRadius: 8,
          background: 'var(--surface-2)',
          border: '1px solid var(--separator)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: 16,
          color: 'var(--text-tertiary)',
        }}>
          {icon}
        </div>
      )}
      <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: 6 }}>{title}</h3>
      <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: 20, lineHeight: 1.5 }}>
        {description}
      </p>
      {action && (
        <button
          className="btn btn-primary"
          onClick={() => {
            if (action.onClick) action.onClick();
            else if (action.href) navigate(action.href);
          }}
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

// ── Pre-built Empty States ───────────────────────────────────────────

export function EmptyPortfolio() {
  return (
    <EmptyState
      icon={<Briefcase className="h-6 w-6" />}
      title="No portfolios yet"
      description="Create your first debt portfolio to begin optimization analysis. You can import from Excel or enter instruments manually."
      action={{ label: "Create Portfolio", href: "/portfolios/new" }}
    />
  );
}

export function EmptyOptimization() {
  return (
    <EmptyState
      icon={<TrendingUp className="h-6 w-6" />}
      title="No optimization results"
      description="Run your first optimization to compare strategies, evaluate tradeoffs, and identify potential savings."
      action={{ label: "Run Optimization", href: "/optimizations/new" }}
    />
  );
}

export function EmptyRiskAnalysis() {
  return (
    <EmptyState
      icon={<Shield className="h-6 w-6" />}
      title="No risk data available"
      description="Risk analysis requires a portfolio with instruments. Create or import a portfolio to see stress tests, VaR, and scenario analysis."
      action={{ label: "Create Portfolio", href: "/portfolios/new" }}
    />
  );
}

export function EmptyDecisions() {
  return (
    <EmptyState
      icon={<FileText className="h-6 w-6" />}
      title="No decisions recorded"
      description="The Flight Recorder tracks every major decision with full context. Run an optimization to create your first decision record."
      action={{ label: "Run Optimization", href: "/optimizations/new" }}
    />
  );
}

export function EmptyExcelImport() {
  return (
    <EmptyState
      icon={<Upload className="h-6 w-6" />}
      title="Import from Excel"
      description="Drag and drop your existing spreadsheet. Quantive will detect portfolio data, scenarios, and assumptions automatically."
      action={{ label: "Choose File", onClick: () => document.getElementById('excel-upload')?.click() }}
    />
  );
}

export function EmptySimulation() {
  return (
    <EmptyState
      icon={<Play className="h-6 w-6" />}
      title="No simulations run"
      description="Create a scenario to simulate market conditions and see how your portfolio responds to rate changes, FX shocks, or credit events."
      action={{ label: "Create Scenario", href: "/whatif" }}
    />
  );
}
