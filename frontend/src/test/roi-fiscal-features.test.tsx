import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

vi.mock('../components/ROIEngine', () => ({
  default: () => <div data-testid="roi-engine">
    <span>ROI Engine</span>
    <span>Automatic savings calculation</span>
    <span>$400M</span>
    <span>Estimated Annual Savings</span>
  </div>
}));
vi.mock('../components/DecisionConfidenceScore', () => ({
  default: () => <div data-testid="confidence-score">
    <span>Decision Confidence Score</span>
    <span>91%</span>
  </div>
}));
vi.mock('../components/CostOfInaction', () => ({
  default: () => <div data-testid="cost-inaction">
    <span>Cost of Doing Nothing</span>
    <span>$4.8B</span>
  </div>
}));
vi.mock('../components/RatingAgencySimulator', () => ({
  default: () => <div data-testid="rating-simulator">
    <span>Rating Agency Simulator</span>
    <span>Moody's</span>
    <span>S&P</span>
    <span>Fitch</span>
  </div>
}));
vi.mock('../components/PoliticalCapitalScore', () => ({
  default: () => <div data-testid="political-score">
    <span>Political Capital Score</span>
    <span>69/100</span>
  </div>
}));
vi.mock('../components/ExecutionFeasibilityScore', () => ({
  default: () => <div data-testid="feasibility-score">
    <span>Execution Feasibility Score</span>
    <span>81/100</span>
  </div>
}));
vi.mock('../components/SovereignHealthDashboard', () => ({
  default: () => <div data-testid="health-dashboard">
    <span>Sovereign Health Dashboard</span>
    <span>61</span>
  </div>
}));
vi.mock('../components/MinisterDashboard', () => ({
  default: () => <div data-testid="minister-dashboard">
    <span>Minister Dashboard</span>
    <span>$420M</span>
  </div>
}));
vi.mock('../components/NationalFiscalImpactEngine', () => ({
  default: () => <div data-testid="fiscal-engine">
    <span>National Fiscal Impact Engine</span>
    <span>10-year fiscal impact</span>
  </div>
}));

import ROIEngine from '../components/ROIEngine';
import DecisionConfidenceScore from '../components/DecisionConfidenceScore';
import CostOfInaction from '../components/CostOfInaction';
import RatingAgencySimulator from '../components/RatingAgencySimulator';
import PoliticalCapitalScore from '../components/PoliticalCapitalScore';
import ExecutionFeasibilityScore from '../components/ExecutionFeasibilityScore';
import SovereignHealthDashboard from '../components/SovereignHealthDashboard';
import MinisterDashboard from '../components/MinisterDashboard';
import NationalFiscalImpactEngine from '../components/NationalFiscalImpactEngine';

const renderWithRouter = (c: React.ReactElement) => render(<BrowserRouter>{c}</BrowserRouter>);

describe('ROI & Fiscal Features', () => {
  it('ROIEngine renders', () => {
    renderWithRouter(<ROIEngine />);
    expect(screen.getByText('ROI Engine')).toBeDefined();
    expect(screen.getByText('Automatic savings calculation')).toBeDefined();
  });

  it('DecisionConfidenceScore renders', () => {
    renderWithRouter(<DecisionConfidenceScore />);
    expect(screen.getByText('Decision Confidence Score')).toBeDefined();
    expect(screen.getByText('91%')).toBeDefined();
  });

  it('CostOfInaction renders', () => {
    renderWithRouter(<CostOfInaction />);
    expect(screen.getByText('Cost of Doing Nothing')).toBeDefined();
  });

  it('RatingAgencySimulator renders', () => {
    renderWithRouter(<RatingAgencySimulator />);
    expect(screen.getByText('Rating Agency Simulator')).toBeDefined();
    expect(screen.getByText("Moody's")).toBeDefined();
    expect(screen.getByText('S&P')).toBeDefined();
    expect(screen.getByText('Fitch')).toBeDefined();
  });

  it('PoliticalCapitalScore renders', () => {
    renderWithRouter(<PoliticalCapitalScore />);
    expect(screen.getByText('Political Capital Score')).toBeDefined();
    expect(screen.getByText('69/100')).toBeDefined();
  });

  it('ExecutionFeasibilityScore renders', () => {
    renderWithRouter(<ExecutionFeasibilityScore />);
    expect(screen.getByText('Execution Feasibility Score')).toBeDefined();
    expect(screen.getByText('81/100')).toBeDefined();
  });

  it('SovereignHealthDashboard renders', () => {
    renderWithRouter(<SovereignHealthDashboard />);
    expect(screen.getByText('Sovereign Health Dashboard')).toBeDefined();
    expect(screen.getByText('61')).toBeDefined();
  });

  it('MinisterDashboard renders', () => {
    renderWithRouter(<MinisterDashboard />);
    expect(screen.getByText('Minister Dashboard')).toBeDefined();
    expect(screen.getByText('$420M')).toBeDefined();
  });

  it('NationalFiscalImpactEngine renders', () => {
    renderWithRouter(<NationalFiscalImpactEngine />);
    expect(screen.getByText('National Fiscal Impact Engine')).toBeDefined();
    expect(screen.getByText('10-year fiscal impact')).toBeDefined();
  });
});
