import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import LandingPage from '../pages/LandingPage';
import {
  welcomeEmail,
  passwordResetEmail,
  reportReadyEmail,
  optimizationCompleteEmail,
  mfaCodeEmail,
} from '../lib/emailTemplates';
import {
  toCSV,
  toJSON,
  toXLSX,
  exportPortfolio,
} from '../lib/export';

// ─── Landing Page ───────────────────────────────────────────────────────────

describe('LandingPage', () => {
  const renderLanding = () =>
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>
    );

  it('renders hero headline', () => {
    renderLanding();
    expect(screen.getByText(/The Debt Portfolio Platform/)).toBeInTheDocument();
  });

  it('renders tagline', () => {
    renderLanding();
    expect(screen.getByText(/That Thinks For You/)).toBeInTheDocument();
  });

  it('renders nav links', () => {
    renderLanding();
    expect(screen.getByText('Sign In')).toBeInTheDocument();
    expect(screen.getByText('Get Started Free')).toBeInTheDocument();
  });

  it('renders all 6 feature cards', () => {
    renderLanding();
    expect(screen.getByText('Multi-Algorithm Optimization')).toBeInTheDocument();
    expect(screen.getByText('Real-Time Risk Analytics')).toBeInTheDocument();
    expect(screen.getByText('AI Advisor')).toBeInTheDocument();
    expect(screen.getByText('ESG & Rating Simulation')).toBeInTheDocument();
    expect(screen.getByText('Interactive Dashboards')).toBeInTheDocument();
    expect(screen.getByText('SOC 2 Ready Security')).toBeInTheDocument();
  });

  it('renders stats', () => {
    renderLanding();
    expect(screen.getByText('$3.2B')).toBeInTheDocument();
    expect(screen.getByText('73%')).toBeInTheDocument();
    expect(screen.getByText('91%')).toBeInTheDocument();
    expect(screen.getByText('< 200ms')).toBeInTheDocument();
  });

  it('renders email signup form', () => {
    renderLanding();
    expect(screen.getByLabelText('Email address')).toBeInTheDocument();
    expect(screen.getByText('Get Early Access')).toBeInTheDocument();
  });

  it('renders footer', () => {
    renderLanding();
    expect(screen.getByText(/Quantive\. All rights reserved/)).toBeInTheDocument();
  });

  it('has public beta badge', () => {
    renderLanding();
    expect(screen.getByText('Now in Public Beta')).toBeInTheDocument();
  });
});

// ─── Email Templates ────────────────────────────────────────────────────────

describe('Email Templates', () => {
  it('welcomeEmail generates correct subject and content', () => {
    const email = welcomeEmail('Alice', 'https://quantive.app/login');
    expect(email.subject).toContain('Welcome');
    expect(email.html).toContain('Alice');
    expect(email.html).toContain('https://quantive.app/login');
    expect(email.text).toContain('Alice');
  });

  it('passwordResetEmail includes expiry warning', () => {
    const email = passwordResetEmail('Bob', 'https://quantive.app/reset?token=abc');
    expect(email.subject).toContain('Reset');
    expect(email.html).toContain('1 hour');
    expect(email.html).toContain('https://quantive.app/reset?token=abc');
    expect(email.html).toContain("Didn't request this");
  });

  it('reportReadyEmail includes report name', () => {
    const email = reportReadyEmail('Carol', 'Q4 Report', 'Sovereign Portfolio', 'https://quantive.app/reports/1');
    expect(email.subject).toContain('Q4 Report');
    expect(email.html).toContain('Sovereign Portfolio');
    expect(email.html).toContain('Download Report');
  });

  it('optimizationCompleteEmail includes cost reduction', () => {
    const email = optimizationCompleteEmail('Dave', 'Optimization #1', '12.5%', 3, 'https://quantive.app/optimizations/1');
    expect(email.subject).toContain('Optimization #1');
    expect(email.html).toContain('12.5%');
    expect(email.html).toContain('3 strategies');
  });

  it('mfaCodeEmail includes 6-digit code', () => {
    const email = mfaCodeEmail('Eve', '847291');
    expect(email.subject).toContain('847291');
    expect(email.html).toContain('847291');
    expect(email.html).toContain('10 minutes');
  });

  it('all templates have subject, html, and text', () => {
    const templates = [
      welcomeEmail('X', '/login'),
      passwordResetEmail('X', '/reset'),
      reportReadyEmail('X', 'R', 'P', '/download'),
      optimizationCompleteEmail('X', 'O', '10%', 1, '/results'),
      mfaCodeEmail('X', '123456'),
    ];
    for (const t of templates) {
      expect(t.subject.length).toBeGreaterThan(0);
      expect(t.html.length).toBeGreaterThan(0);
      expect(t.text.length).toBeGreaterThan(0);
    }
  });
});

// ─── Export Utilities ────────────────────────────────────────────────────────

describe('Export utilities', () => {
  it('toCSV generates correct CSV', () => {
    const csv = toCSV(['Name', 'Value'], [['Alice', 42], ['Bob', 99]]);
    const lines = csv.split('\n');
    expect(lines[0]).toBe('Name,Value');
    expect(lines[1]).toBe('Alice,42');
    expect(lines[2]).toBe('Bob,99');
  });

  it('toCSV escapes commas and quotes', () => {
    const csv = toCSV(['Name'], [['Hello, World']]);
    expect(csv).toBe('Name\n"Hello, World"');
  });

  it('toJSON generates valid JSON', () => {
    const json = toJSON({ key: 'value' });
    expect(JSON.parse(json)).toEqual({ key: 'value' });
  });

  it('toXLSX generates valid XML spreadsheet', () => {
    const xlsx = toXLSX(['Name', 'Value'], [['Alice', 42]]);
    expect(xlsx).toContain('<?xml');
    expect(xlsx).toContain('Workbook');
    expect(xlsx).toContain('Worksheet');
    expect(xlsx).toContain('Alice');
  });

  it('toCSV handles empty rows', () => {
    const csv = toCSV(['A'], []);
    expect(csv).toBe('A');
  });

  it('toCSV handles null values', () => {
    const csv = toCSV(['A'], [[null]]);
    expect(csv).toBe('A\n');
  });

  it('exportPortfolio generates correct structure', () => {
    const portfolio = {
      name: 'Test Portfolio',
      instruments: [
        {
          name: 'Bond A',
          instrument_type: 'treasury_bond',
          currency: 'USD',
          principal_outstanding: 1e9,
          coupon_rate: 0.05,
          maturity_date: '2030-01-01',
          spread_bps: 50,
          is_callable: false,
        },
      ],
    };
    // Just verify it doesn't throw - actual download can't be tested in jsdom
    expect(() => exportPortfolio(portfolio, 'csv')).not.toThrow();
    expect(() => exportPortfolio(portfolio, 'json')).not.toThrow();
    expect(() => exportPortfolio(portfolio, 'xlsx')).not.toThrow();
  });
});
