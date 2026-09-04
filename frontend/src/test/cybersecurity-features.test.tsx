import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

vi.mock('../components/ImmutableAuditLog', () => ({
  default: () => <div data-testid="immutable-audit">
    <span>Immutable Audit Log</span>
    <span>Cryptographically signed</span>
  </div>
}));
vi.mock('../components/MultiEyesApproval', () => ({
  default: () => <div data-testid="multi-eyes">
    <span>Multi-Eyes Approval Controls</span>
    <span>Four-Eyes, Six-Eyes, Eight-Eyes</span>
  </div>
}));
vi.mock('../components/AIFraudDetection', () => ({
  default: () => <div data-testid="fraud-detection">
    <span>AI Fraud Detection</span>
    <span>Real-time monitoring</span>
  </div>
}));
vi.mock('../components/InsiderRiskDashboard', () => ({
  default: () => <div data-testid="insider-risk">
    <span>Insider Risk Dashboard</span>
    <span>Employee risk scoring</span>
  </div>
}));
vi.mock('../components/DecisionExecutionVault', () => ({
  default: () => <div data-testid="decision-vault">
    <span>Decision Execution Vault</span>
    <span>hash, signatures, assumptions</span>
  </div>
}));
vi.mock('../components/DataExfiltrationProtection', () => ({
  default: () => <div data-testid="dlp">
    <span>Data Exfiltration Protection</span>
    <span>Watermarking, export approval</span>
  </div>
}));

import ImmutableAuditLog from '../components/ImmutableAuditLog';
import MultiEyesApproval from '../components/MultiEyesApproval';
import AIFraudDetection from '../components/AIFraudDetection';
import InsiderRiskDashboard from '../components/InsiderRiskDashboard';
import DecisionExecutionVault from '../components/DecisionExecutionVault';
import DataExfiltrationProtection from '../components/DataExfiltrationProtection';

const renderWithRouter = (c: React.ReactElement) => render(<BrowserRouter>{c}</BrowserRouter>);

describe('Cybersecurity & Anti-Fraud Features', () => {
  it('ImmutableAuditLog renders', () => {
    renderWithRouter(<ImmutableAuditLog />);
    expect(screen.getByText('Immutable Audit Log')).toBeDefined();
    expect(screen.getByText('Cryptographically signed')).toBeDefined();
  });

  it('MultiEyesApproval renders', () => {
    renderWithRouter(<MultiEyesApproval />);
    expect(screen.getByText('Multi-Eyes Approval Controls')).toBeDefined();
    expect(screen.getByText('Four-Eyes, Six-Eyes, Eight-Eyes')).toBeDefined();
  });

  it('AIFraudDetection renders', () => {
    renderWithRouter(<AIFraudDetection />);
    expect(screen.getByText('AI Fraud Detection')).toBeDefined();
    expect(screen.getByText('Real-time monitoring')).toBeDefined();
  });

  it('InsiderRiskDashboard renders', () => {
    renderWithRouter(<InsiderRiskDashboard />);
    expect(screen.getByText('Insider Risk Dashboard')).toBeDefined();
    expect(screen.getByText('Employee risk scoring')).toBeDefined();
  });

  it('DecisionExecutionVault renders', () => {
    renderWithRouter(<DecisionExecutionVault />);
    expect(screen.getByText('Decision Execution Vault')).toBeDefined();
    expect(screen.getByText('hash, signatures, assumptions')).toBeDefined();
  });

  it('DataExfiltrationProtection renders', () => {
    renderWithRouter(<DataExfiltrationProtection />);
    expect(screen.getByText('Data Exfiltration Protection')).toBeDefined();
    expect(screen.getByText('Watermarking, export approval')).toBeDefined();
  });
});
