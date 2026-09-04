import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { PortfolioProvider } from '../stores/portfolio';
import PortfolioSelector from '../components/PortfolioSelector';

// Mock API
vi.mock('../api', () => ({
  api: {
    portfolios: {
      list: vi.fn().mockResolvedValue([
        { id: 'p1', name: 'US IG Corporate', instruments: [{ principal_outstanding: 150_000_000 }], created_at: '2026-01-01', updated_at: '2026-08-20' },
        { id: 'p2', name: 'European Sovereign', instruments: [{ principal_outstanding: 80_000_000 }], created_at: '2026-02-01', updated_at: '2026-08-15' },
      ]),
    },
  },
}));

function renderSelector() {
  return render(
    <MemoryRouter>
      <PortfolioProvider>
        <PortfolioSelector />
      </PortfolioProvider>
    </MemoryRouter>,
  );
}

describe('PortfolioSelector', () => {
  it('renders with default label', async () => {
    renderSelector();
    await waitFor(() => {
      expect(screen.getByText('Select Portfolio')).toBeDefined();
    });
  });

  it('opens dropdown on click', async () => {
    renderSelector();
    await waitFor(() => {
      expect(screen.getByText('Select Portfolio')).toBeDefined();
    });
    fireEvent.click(screen.getByText('Select Portfolio'));
    await waitFor(() => {
      expect(screen.getByText('View All Portfolios →')).toBeDefined();
    });
  });

  it('shows portfolio names in dropdown', async () => {
    renderSelector();
    await waitFor(() => {
      expect(screen.getByText('Select Portfolio')).toBeDefined();
    });
    fireEvent.click(screen.getByText('Select Portfolio'));
    await waitFor(() => {
      expect(screen.getByText('US IG Corporate')).toBeDefined();
      expect(screen.getByText('European Sovereign')).toBeDefined();
    });
  });

  it('selects a portfolio on click', async () => {
    renderSelector();
    await waitFor(() => {
      expect(screen.getByText('Select Portfolio')).toBeDefined();
    });
    fireEvent.click(screen.getByText('Select Portfolio'));
    await waitFor(() => {
      expect(screen.getByText('US IG Corporate')).toBeDefined();
    });
    fireEvent.click(screen.getByText('US IG Corporate'));
    await waitFor(() => {
      expect(screen.getByText('US IG Corporate')).toBeDefined();
    });
  });
});
