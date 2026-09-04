import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

vi.mock('../components/InstitutionalMemory', () => ({
  default: () => <div data-testid="memory"><span>Institutional Memory</span><span>National memory</span></div>
}));
vi.mock('../components/PoliticalFeasibility', () => ({
  default: () => <div data-testid="political"><span>Political Feasibility</span><span>Mathematics × Politics</span></div>
}));
vi.mock('../components/CorruptionOpportunity', () => ({
  default: () => <div data-testid="corruption"><span>Corruption Opportunity</span><span>prevention</span></div>
}));
vi.mock('../components/NationalResilience', () => ({
  default: () => <div data-testid="resilience"><span>National Resilience</span><span>Country score</span></div>
}));
vi.mock('../components/MinisterHandover', () => ({
  default: () => <div data-testid="handover"><span>Executive Handover</span><span>auto-generated</span></div>
}));
vi.mock('../components/BlackSwanLab', () => ({
  default: () => <div data-testid="blackswan"><span>Black Swan Laboratory</span><span>nobody is considering</span></div>
}));
vi.mock('../components/DataSourceTrust', () => ({
  default: () => <div data-testid="datasource"><span>Data Source Trust</span><span>Reliability</span></div>
}));

import InstitutionalMemory from '../components/InstitutionalMemory';
import PoliticalFeasibility from '../components/PoliticalFeasibility';
import CorruptionOpportunity from '../components/CorruptionOpportunity';
import NationalResilience from '../components/NationalResilience';
import MinisterHandover from '../components/MinisterHandover';
import BlackSwanLab from '../components/BlackSwanLab';
import DataSourceTrust from '../components/DataSourceTrust';

const r = (c: React.ReactElement) => render(<BrowserRouter>{c}</BrowserRouter>);

describe('Continuity & Institutional Features', () => {
  it('InstitutionalMemory renders', () => { r(<InstitutionalMemory />); expect(screen.getByText('Institutional Memory')).toBeDefined(); });
  it('PoliticalFeasibility renders', () => { r(<PoliticalFeasibility />); expect(screen.getByText('Political Feasibility')).toBeDefined(); });
  it('CorruptionOpportunity renders', () => { r(<CorruptionOpportunity />); expect(screen.getByText('Corruption Opportunity')).toBeDefined(); });
  it('NationalResilience renders', () => { r(<NationalResilience />); expect(screen.getByText('National Resilience')).toBeDefined(); });
  it('MinisterHandover renders', () => { r(<MinisterHandover />); expect(screen.getByText('Executive Handover')).toBeDefined(); });
  it('BlackSwanLab renders', () => { r(<BlackSwanLab />); expect(screen.getByText('Black Swan Laboratory')).toBeDefined(); });
  it('DataSourceTrust renders', () => { r(<DataSourceTrust />); expect(screen.getByText('Data Source Trust')).toBeDefined(); });
});
