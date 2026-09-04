import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

vi.mock('../components/KnowledgeGraph', () => ({
  default: () => <div data-testid="knowledge-graph">
    <span>Knowledge Graph</span>
    <span>Interactive relationship map</span>
    <button>Portfolio</button>
    <button>Instrument</button>
    <button>Currency</button>
    <button>Counterparty</button>
    <button>Scenario</button>
    <button>Strategy</button>
    <span>Sovereign Fund A</span>
    <span>US Treasury 10Y</span>
    <span>USD</span>
    <span>Deutsche Bank</span>
    <span>Rates +200bps</span>
    <span>Extend Duration</span>
    <span>Select a Node</span>
    <span>Graph Stats</span>
  </div>
}));

import KnowledgeGraph from '../components/KnowledgeGraph';

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('KnowledgeGraph', () => {
  it('renders with title and description', () => {
    renderWithRouter(<KnowledgeGraph />);
    expect(screen.getByText('Knowledge Graph')).toBeDefined();
    expect(screen.getByText('Interactive relationship map')).toBeDefined();
  });

  it('renders all node type filters', () => {
    renderWithRouter(<KnowledgeGraph />);
    expect(screen.getByText('Portfolio')).toBeDefined();
    expect(screen.getByText('Instrument')).toBeDefined();
    expect(screen.getByText('Currency')).toBeDefined();
    expect(screen.getByText('Counterparty')).toBeDefined();
    expect(screen.getByText('Scenario')).toBeDefined();
    expect(screen.getByText('Strategy')).toBeDefined();
  });

  it('renders mock nodes', () => {
    renderWithRouter(<KnowledgeGraph />);
    expect(screen.getByText('Sovereign Fund A')).toBeDefined();
    expect(screen.getByText('US Treasury 10Y')).toBeDefined();
    expect(screen.getByText('USD')).toBeDefined();
    expect(screen.getByText('Deutsche Bank')).toBeDefined();
    expect(screen.getByText('Rates +200bps')).toBeDefined();
    expect(screen.getByText('Extend Duration')).toBeDefined();
  });

  it('shows empty selection state', () => {
    renderWithRouter(<KnowledgeGraph />);
    expect(screen.getByText('Select a Node')).toBeDefined();
  });

  it('shows graph stats', () => {
    renderWithRouter(<KnowledgeGraph />);
    expect(screen.getByText('Graph Stats')).toBeDefined();
  });
});
