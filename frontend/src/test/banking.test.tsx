import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { centsToUsd, dollarsToCents } from '../api';
import BankingPage from '../pages/BankingPage';

describe('banking money utils', () => {
  it('formats cents as USD without float drift', () => {
    expect(centsToUsd(18_429_000)).toBe('$184,290.00');
    expect(centsToUsd(0)).toBe('$0.00');
    expect(centsToUsd(1)).toBe('$0.01');
  });

  it('parses dollars to integer cents', () => {
    expect(dollarsToCents('1250.00')).toBe(125_000);
    expect(dollarsToCents('0.01')).toBe(1);
    expect(() => dollarsToCents('0')).toThrow();
    expect(() => dollarsToCents('abc')).toThrow();
  });
});

describe('BankingPage', () => {
  it('renders the 0-fee headline and waitlist', () => {
    render(
      <MemoryRouter>
        <BankingPage />
      </MemoryRouter>,
    );
    expect(screen.getByText(/0% transaction fees/i)).toBeTruthy();
    expect(screen.getByPlaceholderText('you@company.com')).toBeTruthy();
  });
});
