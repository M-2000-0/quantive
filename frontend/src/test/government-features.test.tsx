import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

// Mock all government components
vi.mock('../components/ApprovalWorkflowSystem', () => ({
  default: () => <div data-testid="approval-workflow">
    <span>Cabinet Approval Workflow</span>
    <span>Multi-level government approval</span>
  </div>
}));
vi.mock('../components/PolicyImpactSimulator', () => ({
  default: () => <div data-testid="policy-impact">
    <span>Policy Impact Simulator</span>
    <span>political, economic, and social consequences</span>
  </div>
}));
vi.mock('../components/SovereignDSA', () => ({
  default: () => <div data-testid="sovereign-dsa">
    <span>Sovereign Debt Sustainability</span>
    <span>IMF, World Bank, ECB & BIS</span>
  </div>
}));
vi.mock('../components/CrisisCommandCenter', () => ({
  default: () => <div data-testid="crisis-command">
    <span>Crisis Command Center</span>
    <span>Emergency scenarios, liquidity forecasts</span>
  </div>
}));
vi.mock('../components/GeopoliticalIntelligence', () => ({
  default: () => <div data-testid="geopolitical">
    <span>Geopolitical Intelligence</span>
    <span>Real-time monitoring of geopolitical risks</span>
  </div>
}));
vi.mock('../components/NationalDigitalTwin', () => ({
  default: () => <div data-testid="national-twin">
    <span>National Digital Twin</span>
    <span>Simulate the entire country</span>
  </div>
}));
vi.mock('../components/SovereignAIAdvisor', () => ({
  default: () => <div data-testid="sovereign-advisor">
    <span>Sovereign AI Advisor</span>
    <span>minister-grade recommendations</span>
  </div>
}));
vi.mock('../components/EarlyWarningSystem', () => ({
  default: () => <div data-testid="early-warning">
    <span>Early Warning System</span>
    <span>Predictive alerts before debt crises</span>
  </div>
}));
vi.mock('../components/DebtIssuancePlanner', () => ({
  default: () => <div data-testid="issuance-planner">
    <span>Debt Issuance Planner</span>
    <span>AI-recommended bond issuances</span>
  </div>
}));
vi.mock('../components/CrossCountryBenchmarking', () => ({
  default: () => <div data-testid="cross-country">
    <span>Cross-Country Benchmarking</span>
    <span>Compare sovereign debt metrics</span>
  </div>
}));

import ApprovalWorkflowSystem from '../components/ApprovalWorkflowSystem';
import PolicyImpactSimulator from '../components/PolicyImpactSimulator';
import SovereignDSA from '../components/SovereignDSA';
import CrisisCommandCenter from '../components/CrisisCommandCenter';
import GeopoliticalIntelligence from '../components/GeopoliticalIntelligence';
import NationalDigitalTwin from '../components/NationalDigitalTwin';
import SovereignAIAdvisor from '../components/SovereignAIAdvisor';
import EarlyWarningSystem from '../components/EarlyWarningSystem';
import DebtIssuancePlanner from '../components/DebtIssuancePlanner';
import CrossCountryBenchmarking from '../components/CrossCountryBenchmarking';

const renderWithRouter = (c: React.ReactElement) => render(<BrowserRouter>{c}</BrowserRouter>);

describe('Government Features', () => {
  it('ApprovalWorkflow renders', () => {
    renderWithRouter(<ApprovalWorkflowSystem />);
    expect(screen.getByText('Cabinet Approval Workflow')).toBeDefined();
    expect(screen.getByText('Multi-level government approval')).toBeDefined();
  });

  it('PolicyImpact renders', () => {
    renderWithRouter(<PolicyImpactSimulator />);
    expect(screen.getByText('Policy Impact Simulator')).toBeDefined();
    expect(screen.getByText('political, economic, and social consequences')).toBeDefined();
  });

  it('SovereignDSA renders', () => {
    renderWithRouter(<SovereignDSA />);
    expect(screen.getByText('Sovereign Debt Sustainability')).toBeDefined();
    expect(screen.getByText('IMF, World Bank, ECB & BIS')).toBeDefined();
  });

  it('CrisisCommand renders', () => {
    renderWithRouter(<CrisisCommandCenter />);
    expect(screen.getByText('Crisis Command Center')).toBeDefined();
    expect(screen.getByText('Emergency scenarios, liquidity forecasts')).toBeDefined();
  });

  it('Geopolitical renders', () => {
    renderWithRouter(<GeopoliticalIntelligence />);
    expect(screen.getByText('Geopolitical Intelligence')).toBeDefined();
    expect(screen.getByText('Real-time monitoring of geopolitical risks')).toBeDefined();
  });

  it('NationalTwin renders', () => {
    renderWithRouter(<NationalDigitalTwin />);
    expect(screen.getByText('National Digital Twin')).toBeDefined();
    expect(screen.getByText('Simulate the entire country')).toBeDefined();
  });

  it('SovereignAdvisor renders', () => {
    renderWithRouter(<SovereignAIAdvisor />);
    expect(screen.getByText('Sovereign AI Advisor')).toBeDefined();
    expect(screen.getByText('minister-grade recommendations')).toBeDefined();
  });

  it('EarlyWarning renders', () => {
    renderWithRouter(<EarlyWarningSystem />);
    expect(screen.getByText('Early Warning System')).toBeDefined();
    expect(screen.getByText('Predictive alerts before debt crises')).toBeDefined();
  });

  it('IssuancePlanner renders', () => {
    renderWithRouter(<DebtIssuancePlanner />);
    expect(screen.getByText('Debt Issuance Planner')).toBeDefined();
    expect(screen.getByText('AI-recommended bond issuances')).toBeDefined();
  });

  it('CrossCountry renders', () => {
    renderWithRouter(<CrossCountryBenchmarking />);
    expect(screen.getByText('Cross-Country Benchmarking')).toBeDefined();
    expect(screen.getByText('Compare sovereign debt metrics')).toBeDefined();
  });
});
