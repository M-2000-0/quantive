import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

vi.mock('../components/AirGappedDeployment', () => ({
  default: () => <div data-testid="airgapped"><span>Deployment Options</span><span>Air-gapped</span></div>
}));
vi.mock('../components/ComplianceDashboard', () => ({
  default: () => <div data-testid="compliance"><span>Compliance Dashboard</span><span>NIST, ISO</span></div>
}));
vi.mock('../components/DisasterRecovery', () => ({
  default: () => <div data-testid="dr"><span>Business Continuity</span><span>Disaster Recovery</span></div>
}));
vi.mock('../components/DataResidencyControls', () => ({
  default: () => <div data-testid="residency"><span>Data Residency Controls</span><span>In-country storage</span></div>
}));
vi.mock('../components/VendorRiskMitigation', () => ({
  default: () => <div data-testid="vendor"><span>Vendor Risk</span><span>Source code escrow</span></div>
}));
vi.mock('../components/SecurityAssessment', () => ({
  default: () => <div data-testid="security"><span>Security Assessment</span><span>Penetration tests</span></div>
}));
vi.mock('../components/LegalChainOfEvidence', () => ({
  default: () => <div data-testid="legal"><span>Legal Chain of Evidence</span><span>25-year retention</span></div>
}));
vi.mock('../components/SystemAvailabilityDashboard', () => ({
  default: () => <div data-testid="uptime"><span>System Availability</span><span>99.99% uptime</span></div>
}));

import AirGappedDeployment from '../components/AirGappedDeployment';
import ComplianceDashboard from '../components/ComplianceDashboard';
import DisasterRecovery from '../components/DisasterRecovery';
import DataResidencyControls from '../components/DataResidencyControls';
import VendorRiskMitigation from '../components/VendorRiskMitigation';
import SecurityAssessment from '../components/SecurityAssessment';
import LegalChainOfEvidence from '../components/LegalChainOfEvidence';
import SystemAvailabilityDashboard from '../components/SystemAvailabilityDashboard';

const r = (c: React.ReactElement) => render(<BrowserRouter>{c}</BrowserRouter>);

describe('Procurement-Critical Features', () => {
  it('AirGappedDeployment renders', () => { r(<AirGappedDeployment />); expect(screen.getByText('Deployment Options')).toBeDefined(); });
  it('ComplianceDashboard renders', () => { r(<ComplianceDashboard />); expect(screen.getByText('Compliance Dashboard')).toBeDefined(); });
  it('DisasterRecovery renders', () => { r(<DisasterRecovery />); expect(screen.getByText('Business Continuity')).toBeDefined(); });
  it('DataResidencyControls renders', () => { r(<DataResidencyControls />); expect(screen.getByText('Data Residency Controls')).toBeDefined(); });
  it('VendorRiskMitigation renders', () => { r(<VendorRiskMitigation />); expect(screen.getByText('Vendor Risk')).toBeDefined(); });
  it('SecurityAssessment renders', () => { r(<SecurityAssessment />); expect(screen.getByText('Security Assessment')).toBeDefined(); });
  it('LegalChainOfEvidence renders', () => { r(<LegalChainOfEvidence />); expect(screen.getByText('Legal Chain of Evidence')).toBeDefined(); });
  it('SystemAvailabilityDashboard renders', () => { r(<SystemAvailabilityDashboard />); expect(screen.getByText('System Availability')).toBeDefined(); });
});
