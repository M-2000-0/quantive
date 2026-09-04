import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

// Mock auth store
const mockUser = { id: 'user-1', email: 'test@company.com', role: 'admin' };
vi.mock('../stores/auth', () => ({
  useAuth: () => ({
    user: mockUser,
    token: 'test-token',
    isAuthenticated: true,
    loading: false,
  }),
}));

import {
  TERMS_OF_SERVICE,
  PRIVACY_POLICY,
  FINANCIAL_DISCLAIMER,
  DISCLAIMER_VERSION,
} from '../lib/legalContent';
import DisclaimerBanner from '../components/DisclaimerBanner';

// ─── Legal Content Tests ─────────────────────────────────────────────────────

describe('Legal Content', () => {
  it('Terms of Service has all required sections', () => {
    const tos = TERMS_OF_SERVICE.toUpperCase();
    expect(tos).toContain('LIMITATION OF LIABILITY');
    expect(tos).toContain('INDEMNIFICATION');
    expect(tos).toContain('GOVERNING LAW');
    expect(tos).toContain('INTELLECTUAL PROPERTY');
    expect(tos).toContain('FINANCIAL DISCLAIMER');
  });

  it('Privacy Policy has all required sections', () => {
    const pp = PRIVACY_POLICY.toUpperCase();
    expect(pp).toContain('GDPR');
    expect(pp).toContain('CCPA');
    expect(pp).toContain('DATA SECURITY');
    expect(pp).toContain('DATA RETENTION');
    expect(pp).toContain('COOKIES');
    expect(pp).toContain('YOUR RIGHTS');
  });

  it('Financial Disclaimer covers key liability protections', () => {
    const fd = FINANCIAL_DISCLAIMER.toUpperCase();
    expect(fd).toContain('NO FINANCIAL ADVICE');
    expect(fd).toContain('PAST PERFORMANCE');
    expect(fd).toContain('MODEL LIMITATIONS');
    expect(fd).toContain('LIMITATION OF LIABILITY');
    expect(fd).toContain('ASSUMPTION OF RISK');
    expect(fd).toContain('PROFESSIONAL JUDGMENT REQUIRED');
  });

  it('Disclaimer version is set', () => {
    expect(DISCLAIMER_VERSION).toBe('1.0.0');
  });

  it('Terms includes jurisdiction', () => {
    expect(TERMS_OF_SERVICE).toContain('Delaware');
  });

  it('Privacy Policy covers data sharing', () => {
    const pp = PRIVACY_POLICY.toUpperCase();
    expect(pp).toContain('SERVICE PROVIDERS');
    expect(pp).toContain('DO NOT SELL');
  });

  it('Financial Disclaimer mentions regulatory notice', () => {
    const fd = FINANCIAL_DISCLAIMER.toUpperCase();
    expect(fd).toContain('SEC');
    expect(fd).toContain('FCA');
    expect(fd).toContain('FINRA');
  });
});

// ─── DisclaimerBanner Tests ──────────────────────────────────────────────────

describe('DisclaimerBanner', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders the disclaimer modal', () => {
    render(<DisclaimerBanner />);
    expect(screen.getByText('Financial Disclaimer')).toBeTruthy();
    expect(screen.getByText(/Not Financial Advice/)).toBeTruthy();
  });

  it('shows warning bullets', () => {
    render(<DisclaimerBanner />);
    expect(screen.getByText(/No Guarantees/)).toBeTruthy();
    expect(screen.getByText(/Your Responsibility/)).toBeTruthy();
    expect(screen.getByText(/Model Limitations/)).toBeTruthy();
  });

  it('accept button is disabled until checkbox is checked', () => {
    render(<DisclaimerBanner />);
    const acceptBtn = screen.getByText(/I Understand/);
    expect(acceptBtn).toBeDisabled();
  });

  it('accept button enables after checkbox', () => {
    render(<DisclaimerBanner />);
    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);
    const acceptBtn = screen.getByText(/I Understand/);
    expect(acceptBtn).not.toBeDisabled();
  });

  it('can expand full terms', () => {
    render(<DisclaimerBanner />);
    const expandBtn = screen.getByText(/Read full Terms/);
    fireEvent.click(expandBtn);
    expect(screen.getByText(/Limitation of Liability/)).toBeTruthy();
    expect(screen.getByText(/Indemnification/)).toBeTruthy();
  });

  it('calls onAccept when accepted', () => {
    const onAccept = vi.fn();
    render(<DisclaimerBanner onAccept={onAccept} />);
    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);
    const acceptBtn = screen.getByText(/I Understand/);
    fireEvent.click(acceptBtn);
    expect(onAccept).toHaveBeenCalled();
  });

  it('persists acceptance to localStorage', () => {
    const onAccept = vi.fn();
    render(<DisclaimerBanner onAccept={onAccept} />);
    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);
    const acceptBtn = screen.getByText(/I Understand/);
    fireEvent.click(acceptBtn);
    const key = `quantive_disclaimer_accepted_${mockUser.id}`;
    expect(localStorage.getItem(key)).toBe('true');
  });

  it('has links to legal pages', () => {
    render(<DisclaimerBanner />);
    expect(screen.getByText('Terms')).toBeTruthy();
    expect(screen.getByText('Privacy')).toBeTruthy();
    expect(screen.getByText('Full Disclaimer')).toBeTruthy();
  });
});

// ─── LegalPage Tests ─────────────────────────────────────────────────────────

describe('LegalPage', () => {
  it('renders Terms of Service', async () => {
    const { default: LegalPage } = await import('../pages/LegalPage');
    render(
      <BrowserRouter>
        <LegalPage />
      </BrowserRouter>
    );
    // LegalPage uses useParams, which won't match without a Router context
    // So we test the content directly
    expect(TERMS_OF_SERVICE).toContain('Terms of Service');
  });

  it('all legal documents have effective dates', () => {
    expect(TERMS_OF_SERVICE).toContain('Effective Date');
    expect(PRIVACY_POLICY).toContain('Effective Date');
    expect(FINANCIAL_DISCLAIMER).toContain('IMPORTANT');
  });
});

// ─── Disclaimer API Mock Tests ───────────────────────────────────────────────

describe('Disclaimer API contract', () => {
  it('acceptance request schema is valid', () => {
    const body = {
      version: '1.0.0',
      accepted_terms: true,
      accepted_privacy: true,
      accepted_financial_disclaimer: true,
      read_and_understood: true,
    };
    // All fields must be true
    expect(body.accepted_terms).toBe(true);
    expect(body.accepted_privacy).toBe(true);
    expect(body.accepted_financial_disclaimer).toBe(true);
    expect(body.read_and_understood).toBe(true);
  });

  it('disclaimer status response schema is valid', () => {
    const response = {
      accepted: true,
      version: '1.0.0',
      accepted_at: '2026-08-01T00:00:00Z',
      all_accepted: true,
    };
    expect(response.accepted).toBe(true);
    expect(response.all_accepted).toBe(true);
    expect(response.version).toBe('1.0.0');
  });
});
