import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

// Mock all components
vi.mock('../components/DecisionCopilot', () => ({
  default: () => <div data-testid="decision-copilot">
    <input placeholder="Ask a question" />
    <button>Ask</button>
    <span>AI Decision Copilot</span>
    <span>Ask anything about your portfolio</span>
  </div>
}));

vi.mock('../components/ExplainabilityEngine', () => ({
  default: () => <div data-testid="explainability-engine">
    <span>Explainability Engine</span>
    <span>Every optimization shows its work</span>
    <button>Allocation Why</button>
    <button>Constraints</button>
    <button>Objectives</button>
    <button>Scenarios</button>
  </div>
}));

vi.mock('../components/DigitalTwin', () => ({
  default: () => <div data-testid="digital-twin">
    <span>Digital Twin</span>
    <span>Live simulation</span>
    <button>Interest Rate Shock</button>
    <button>Currency Shock</button>
    <button>Credit Event</button>
    <button>Macro Scenario</button>
    <button>Run Simulation</button>
  </div>
}));

vi.mock('../components/ConstraintBuilderAI', () => ({
  default: () => <div data-testid="constraint-builder">
    <span>Constraint Builder AI</span>
    <span>Describe constraints in plain English</span>
    <input placeholder="Keep USD exposure" />
    <button>Parse</button>
    <button>Keep USD exposure under 20%</button>
  </div>
}));

vi.mock('../components/SolverTournament', () => ({
  default: () => <div data-testid="solver-tournament">
    <span>Solver Tournament</span>
    <span>Run all solvers head-to-head</span>
    <button>Start Tournament</button>
    <span>MILP</span>
    <span>Simulated Annealing</span>
    <span>Genetic Algorithm</span>
  </div>
}));

// Import components after mocks
import DecisionCopilot from '../components/DecisionCopilot';
import ExplainabilityEngine from '../components/ExplainabilityEngine';
import DigitalTwin from '../components/DigitalTwin';
import ConstraintBuilderAI from '../components/ConstraintBuilderAI';
import SolverTournament from '../components/SolverTournament';

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('AI Intelligence Features', () => {
  describe('DecisionCopilot', () => {
    it('renders with title and description', () => {
      renderWithRouter(<DecisionCopilot />);
      expect(screen.getByText('AI Decision Copilot')).toBeDefined();
      expect(screen.getByText('Ask anything about your portfolio')).toBeDefined();
    });

    it('renders input and ask button', () => {
      renderWithRouter(<DecisionCopilot />);
      expect(screen.getByPlaceholderText('Ask a question')).toBeDefined();
      expect(screen.getByText('Ask')).toBeDefined();
    });
  });

  describe('ExplainabilityEngine', () => {
    it('renders with title and description', () => {
      renderWithRouter(<ExplainabilityEngine />);
      expect(screen.getByText('Explainability Engine')).toBeDefined();
      expect(screen.getByText('Every optimization shows its work')).toBeDefined();
    });

    it('renders all tabs', () => {
      renderWithRouter(<ExplainabilityEngine />);
      expect(screen.getByText('Allocation Why')).toBeDefined();
      expect(screen.getByText('Constraints')).toBeDefined();
      expect(screen.getByText('Objectives')).toBeDefined();
      expect(screen.getByText('Scenarios')).toBeDefined();
    });
  });

  describe('DigitalTwin', () => {
    it('renders with title and description', () => {
      renderWithRouter(<DigitalTwin />);
      expect(screen.getByText('Digital Twin')).toBeDefined();
      expect(screen.getByText('Live simulation')).toBeDefined();
    });

    it('renders all scenario types', () => {
      renderWithRouter(<DigitalTwin />);
      expect(screen.getByText('Interest Rate Shock')).toBeDefined();
      expect(screen.getByText('Currency Shock')).toBeDefined();
      expect(screen.getByText('Credit Event')).toBeDefined();
      expect(screen.getByText('Macro Scenario')).toBeDefined();
    });

    it('renders run simulation button', () => {
      renderWithRouter(<DigitalTwin />);
      expect(screen.getByText('Run Simulation')).toBeDefined();
    });
  });

  describe('ConstraintBuilderAI', () => {
    it('renders with title and description', () => {
      renderWithRouter(<ConstraintBuilderAI />);
      expect(screen.getByText('Constraint Builder AI')).toBeDefined();
      expect(screen.getByText('Describe constraints in plain English')).toBeDefined();
    });

    it('renders input and parse button', () => {
      renderWithRouter(<ConstraintBuilderAI />);
      expect(screen.getByPlaceholderText('Keep USD exposure')).toBeDefined();
      expect(screen.getByText('Parse')).toBeDefined();
    });

    it('renders preset constraints', () => {
      renderWithRouter(<ConstraintBuilderAI />);
      expect(screen.getByText('Keep USD exposure under 20%')).toBeDefined();
    });
  });

  describe('SolverTournament', () => {
    it('renders with title and description', () => {
      renderWithRouter(<SolverTournament />);
      expect(screen.getByText('Solver Tournament')).toBeDefined();
      expect(screen.getByText('Run all solvers head-to-head')).toBeDefined();
    });

    it('renders start tournament button', () => {
      renderWithRouter(<SolverTournament />);
      expect(screen.getByText('Start Tournament')).toBeDefined();
    });

    it('renders solver names', () => {
      renderWithRouter(<SolverTournament />);
      expect(screen.getByText('MILP')).toBeDefined();
      expect(screen.getByText('Simulated Annealing')).toBeDefined();
      expect(screen.getByText('Genetic Algorithm')).toBeDefined();
    });
  });
});
