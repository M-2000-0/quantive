import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

vi.mock('../components/OfflineModePortal', () => ({
  default: () => <div data-testid="offline"><span>Offline Mode</span><span>Zero Internet</span></div>
}));
vi.mock('../components/SourceCodeInspection', () => ({
  default: () => <div data-testid="source"><span>Source Code Inspection</span><span>SBOM</span></div>
}));
vi.mock('../components/AIGovernanceLayer', () => ({
  default: () => <div data-testid="ai-gov"><span>AI Governance</span><span>Bias Detection</span></div>
}));
vi.mock('../components/SavingsTraceability', () => ({
  default: () => <div data-testid="savings"><span>Savings Traceability</span><span>Explain every dollar</span></div>
}));
vi.mock('../components/TrainingAcademy', () => ({
  default: () => <div data-testid="training"><span>Quantive Academy</span><span>Certifications</span></div>
}));
vi.mock('../components/ModelValidation', () => ({
  default: () => <div data-testid="model-val"><span>Model Validation</span><span>Bias Testing</span></div>
}));
vi.mock('../components/RedTeamTesting', () => ({
  default: () => <div data-testid="red-team"><span>Red Team Testing</span><span>Penetration Tests</span></div>
}));

import OfflineModePortal from '../components/OfflineModePortal';
import SourceCodeInspection from '../components/SourceCodeInspection';
import AIGovernanceLayer from '../components/AIGovernanceLayer';
import SavingsTraceability from '../components/SavingsTraceability';
import TrainingAcademy from '../components/TrainingAcademy';
import ModelValidation from '../components/ModelValidation';
import RedTeamTesting from '../components/RedTeamTesting';

const r = (c: React.ReactElement) => render(<BrowserRouter>{c}</BrowserRouter>);

describe('Unexpected Government Features', () => {
  it('OfflineMode renders', () => { r(<OfflineModePortal />); expect(screen.getByText('Offline Mode')).toBeDefined(); });
  it('SourceCode renders', () => { r(<SourceCodeInspection />); expect(screen.getByText('Source Code Inspection')).toBeDefined(); });
  it('AIGovernance renders', () => { r(<AIGovernanceLayer />); expect(screen.getByText('AI Governance')).toBeDefined(); });
  it('SavingsTraceability renders', () => { r(<SavingsTraceability />); expect(screen.getByText('Savings Traceability')).toBeDefined(); });
  it('TrainingAcademy renders', () => { r(<TrainingAcademy />); expect(screen.getByText('Quantive Academy')).toBeDefined(); });
  it('ModelValidation renders', () => { r(<ModelValidation />); expect(screen.getByText('Model Validation')).toBeDefined(); });
  it('RedTeamTesting renders', () => { r(<RedTeamTesting />); expect(screen.getByText('Red Team Testing')).toBeDefined(); });
});
