import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import QuboWorkspacePage from '../pages/QuboWorkspacePage';

const overview = {
  counts: { new: 1, accepted: 0, dismissed: 0 },
  total: 1,
  potential_new_cents: 3_820_000,
  accepted_cents: 0,
  rules_version: 'QBIZ-2026.1',
  supported_jurisdictions: ['US', 'MX', 'BD'],
  note: 'Amounts are outflows that may qualify — not promised savings.',
};

const findings = {
  findings: [
    {
      id: 'f1',
      account_id: 'a1',
      txn_id: 't1',
      rule_id: 'QBIZ-2026-wages',
      rules_version: 'QBIZ-2026.1',
      jurisdiction: 'US',
      tax_year: 2026,
      category: 'Payroll',
      title: 'Wages & salaries — potentially deductible',
      detail: 'Employee pay is commonly an ordinary business expense.',
      amount_cents: 3_820_000,
      requirements: { requirements: ['payroll records'], docs: ['W-2/W-3'], sources: ['IRS publications — verify'] },
      status: 'new',
      created_at: null,
    },
  ],
};

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: unknown) => {
      const path = String(url);
      if (path.includes('/settings')) {
        return { ok: true, status: 200, json: async () => ({ jurisdiction: 'US', supported_jurisdictions: ['US', 'MX', 'BD'] }) };
      }
      return {
        ok: true,
        status: 200,
        json: async () => (path.includes('/findings') ? findings : overview),
      };
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('QuboWorkspacePage', () => {
  it('renders findings with rule refs and amounts', async () => {
    render(
      <MemoryRouter>
        <QuboWorkspacePage />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByText(/Wages & salaries/)).toBeTruthy());
    expect(screen.getByText(/QBIZ-2026-wages/)).toBeTruthy();
    expect(screen.getAllByText('$38,200.00').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/not promised savings/)).toBeTruthy();
  });
});
