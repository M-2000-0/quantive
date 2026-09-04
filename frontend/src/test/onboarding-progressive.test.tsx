import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import OnboardingWizard from '../components/OnboardingWizard';
import ProgressiveSidebar from '../components/ProgressiveSidebar';

vi.mock('../stores/auth', () => ({
  useAuth: () => ({ user: null, loading: false }),
}));

vi.mock('../stores/demoMode', () => ({
  useDemoMode: () => ({ isDemoMode: false, enterDemoMode: vi.fn() }),
}));

function renderWithRouter(ui: React.ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe('OnboardingWizard', () => {
  it('renders welcome step on mount', () => {
    renderWithRouter(<OnboardingWizard onComplete={vi.fn()} />);
    expect(screen.getByText('Welcome to Quantive')).toBeDefined();
    expect(screen.getByText('Start Onboarding')).toBeDefined();
  });

  it('shows skip button on welcome step', () => {
    renderWithRouter(<OnboardingWizard onComplete={vi.fn()} />);
    expect(screen.getByText('Skip for Now')).toBeDefined();
  });

  it('navigates to import step when Start Onboarding is clicked', () => {
    renderWithRouter(<OnboardingWizard onComplete={vi.fn()} />);
    fireEvent.click(screen.getByText('Start Onboarding'));
    expect(screen.getByText('Import Your Data')).toBeDefined();
  });

  it('shows file format options on import step', () => {
    renderWithRouter(<OnboardingWizard onComplete={vi.fn()} />);
    fireEvent.click(screen.getByText('Start Onboarding'));
    expect(screen.getByText('Bloomberg Excel Export')).toBeDefined();
    expect(screen.getByText('CSV Spreadsheet')).toBeDefined();
    expect(screen.getByText('Excel Workbook')).toBeDefined();
    expect(screen.getByText('JSON Data')).toBeDefined();
  });

  it('shows demo data option', () => {
    renderWithRouter(<OnboardingWizard onComplete={vi.fn()} />);
    fireEvent.click(screen.getByText('Start Onboarding'));
    expect(screen.getByText('Use Demo Data')).toBeDefined();
  });

  it('calls onComplete when Skip is clicked', () => {
    const onComplete = vi.fn();
    renderWithRouter(<OnboardingWizard onComplete={onComplete} />);
    fireEvent.click(screen.getByText('Skip for Now'));
    expect(onComplete).toHaveBeenCalled();
  });

  it('shows progress bar with 5 steps', () => {
    renderWithRouter(<OnboardingWizard onComplete={vi.fn()} />);
    expect(screen.getByText('Step 1 of 5')).toBeDefined();
  });
});

describe('ProgressiveSidebar', () => {
  it('renders in simplified mode by default', () => {
    renderWithRouter(<ProgressiveSidebar collapsed={false} />);
    expect(screen.getByText('Dashboard')).toBeDefined();
    expect(screen.getByText('Portfolio')).toBeDefined();
    expect(screen.getByText('Optimize')).toBeDefined();
    expect(screen.getByText('Simple')).toBeDefined();
    expect(screen.getByText('Full')).toBeDefined();
  });

  it('shows only essential items in simplified mode', () => {
    renderWithRouter(<ProgressiveSidebar collapsed={false} />);
    expect(screen.getByText('Dashboard')).toBeDefined();
    expect(screen.getByText('Market Data')).toBeDefined();
    // Advanced items should not be visible in simplified mode
    expect(screen.queryByText('AI Advisor')).toBeNull();
    expect(screen.queryByText('Digital Twin')).toBeNull();
  });

  it('switches to full mode and shows all items', () => {
    renderWithRouter(<ProgressiveSidebar collapsed={false} />);
    fireEvent.click(screen.getByText('Full'));
    expect(screen.getByText('AI Advisor')).toBeDefined();
    expect(screen.getByText('Digital Twin')).toBeDefined();
    expect(screen.getByText('Knowledge Graph')).toBeDefined();
  });

  it('shows guided setup link', () => {
    renderWithRouter(<ProgressiveSidebar collapsed={false} />);
    expect(screen.getByText('Guided Setup')).toBeDefined();
  });

  it('returns null when collapsed', () => {
    const { container } = renderWithRouter(<ProgressiveSidebar collapsed={true} />);
    expect(container.innerHTML).toBe('');
  });
});
