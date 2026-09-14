import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import PortfoliosPage from '../pages/PortfoliosPage';

const listMock = vi.fn();
const createMock = vi.fn();
const deleteMock = vi.fn();
const seedMock = vi.fn();

vi.mock('../api', () => ({
  api: {
    portfolios: {
      list: (...args: unknown[]) => listMock(...args),
      create: (...args: unknown[]) => createMock(...args),
      delete: (...args: unknown[]) => deleteMock(...args),
    },
    firstRun: {
      createDemoPortfolio: (...args: unknown[]) => seedMock(...args),
    },
  },
}));

const EMPTY = { data: [], meta: { total: 0, page_size: 100, has_more: false, next_cursor: null } };

beforeEach(() => {
  vi.clearAllMocks();
  listMock.mockResolvedValue(EMPTY);
});

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/portfolios']}>
      <Routes>
        <Route path="/portfolios" element={<PortfoliosPage />} />
        <Route path="/dashboard/portfolios/:id" element={<div>detail page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('PortfoliosPage', () => {
  it('shows a guided empty state with demo seed', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('No portfolios yet')).toBeTruthy());
    expect(screen.getByText(/Load demo portfolio/)).toBeTruthy();

    seedMock.mockResolvedValue({ id: 'demo-1', name: 'Demo', instruments_count: 12 });
    await userEvent.click(screen.getByText(/Load demo portfolio/));
    await waitFor(() => expect(seedMock).toHaveBeenCalled());
    expect(await screen.findByText('detail page')).toBeTruthy();
  });

  it('lists portfolios and creates a new one', async () => {
    listMock.mockResolvedValue({
      ...EMPTY,
      data: [{ id: 'p1', name: 'Sovereign Bonds', description: 'USD sleeve', org_id: 'o1' }],
    });
    renderPage();
    expect(await screen.findByText('Sovereign Bonds')).toBeTruthy();

    createMock.mockResolvedValue({ id: 'p2', name: 'New Fund', description: '', org_id: 'o1' });
    await userEvent.type(screen.getByPlaceholderText('Sovereign Bond Portfolio'), 'New Fund');
    await userEvent.click(screen.getByText('Create portfolio'));
    await waitFor(() => expect(createMock).toHaveBeenCalledWith({ name: 'New Fund', description: '' }));
    expect(await screen.findByText('detail page')).toBeTruthy();
  });

  it('deletes after confirm', async () => {
    listMock.mockResolvedValue({
      ...EMPTY,
      data: [{ id: 'p1', name: 'Old Fund', description: '', org_id: 'o1' }],
    });
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
    renderPage();
    expect(await screen.findByText('Old Fund')).toBeTruthy();
    deleteMock.mockResolvedValue(undefined);
    await userEvent.click(screen.getByText('Delete'));
    await waitFor(() => expect(deleteMock).toHaveBeenCalledWith('p1'));
    confirm.mockRestore();
  });
});
