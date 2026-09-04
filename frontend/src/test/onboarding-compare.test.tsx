import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

// Mock chart components
vi.mock('../components/charts/GlassBarChart', () => ({
 default: (props: any) => <div data-testid="glass-bar-chart">{props.title}</div>,
}));
vi.mock('../components/charts/GlassPieChart', () => ({
 default: (props: any) => <div data-testid="glass-pie-chart">{props.title}</div>,
}));

// Mock alertSounds to avoid AudioContext
vi.mock('../lib/alertSounds', () => ({
 getAlertSounds: () => ({
 setVolume: vi.fn(),
 preview: vi.fn(),
 enable: vi.fn(),
 disable: vi.fn(),
 mute: vi.fn(),
 unmute: vi.fn(),
 }),
 severityToSoundType: (s: string) => s,
 signalToSoundType: (s: string) => s,
}));

import NotificationPreferencesPage from '../pages/NotificationPreferencesPage';
import PortfolioComparisonMode from '../components/PortfolioComparisonMode';

const renderWithRouter = (component: React.ReactNode) =>
 render(<BrowserRouter>{component}</BrowserRouter>);

// ── NotificationPreferencesPage Tests ─────────────────────────────────

describe('NotificationPreferencesPage', () => {
 it('renders page title', () => {
 renderWithRouter(<NotificationPreferencesPage />);
 expect(screen.getByText('Notification Preferences')).toBeDefined();
 });

 it('renders all 5 sections', () => {
 renderWithRouter(<NotificationPreferencesPage />);
 expect(screen.getAllByText(/Sound Alerts/).length).toBeGreaterThan(0);
 expect(screen.getAllByText(/Email Notifications/).length).toBeGreaterThan(0);
 expect(screen.getAllByText(/Push Notifications/).length).toBeGreaterThan(0);
 expect(screen.getAllByText(/Webhook Integration/).length).toBeGreaterThan(0);
 expect(screen.getAllByText(/Alert Categories/).length).toBeGreaterThan(0);
 });

 it('shows alert channels and Save button', () => {
 renderWithRouter(<NotificationPreferencesPage />);
 expect(screen.getByText('Price Alerts')).toBeDefined();
 expect(screen.getByText('Save Preferences')).toBeDefined();
 expect(screen.getByText('Volume')).toBeDefined();
 });

 it('toggles email digest mode', () => {
 renderWithRouter(<NotificationPreferencesPage />);
 fireEvent.click(screen.getByText(/Real-time/));
 expect(screen.queryByLabelText('Delivery Time')).toBeNull();
 });

 it('shows webhook URL field after enabling webhook toggle', () => {
 renderWithRouter(<NotificationPreferencesPage />);
 // Find the webhook section's toggle button (last toggle on page)
 const toggles = document.querySelectorAll('button[class*="rounded-full"][class*="w-12"]');
 const webhookToggle = toggles[toggles.length - 1];
 fireEvent.click(webhookToggle);
 expect(screen.getByPlaceholderText(/hooks.slack.com/)).toBeDefined();
 });

 it('shows all 8 alert categories', () => {
 renderWithRouter(<NotificationPreferencesPage />);
 expect(screen.getByText('Price Alerts')).toBeDefined();
 expect(screen.getByText('Maturity Alerts')).toBeDefined();
 expect(screen.getByText('Credit Alerts')).toBeDefined();
 expect(screen.getByText('Optimization Signals')).toBeDefined();
 expect(screen.getByText('Consensus Alerts')).toBeDefined();
 expect(screen.getByText('Market Events')).toBeDefined();
 expect(screen.getByText('Weekly Report')).toBeDefined();
 expect(screen.getByText('Monthly Peer Report')).toBeDefined();
 });
});

// ── PortfolioComparisonMode Tests ─────────────────────────────────────

describe('PortfolioComparisonMode', () => {
 it('renders page title and selectors', () => {
 renderWithRouter(<PortfolioComparisonMode />);
 expect(screen.getByText('Portfolio Comparison')).toBeDefined();
 expect(screen.getByText('PORTFOLIO 1')).toBeDefined();
 expect(screen.getByText('PORTFOLIO 2')).toBeDefined();
 });

 it('shows all 4 metric tabs (lowercase)', () => {
 renderWithRouter(<PortfolioComparisonMode />);
 expect(screen.getAllByText('overview').length).toBeGreaterThan(0);
 expect(screen.getAllByText('allocation').length).toBeGreaterThan(0);
 expect(screen.getAllByText('risk').length).toBeGreaterThan(0);
 expect(screen.getAllByText('instruments').length).toBeGreaterThan(0);
 });

 it('shows overview comparison table with correct metrics', () => {
 renderWithRouter(<PortfolioComparisonMode />);
 expect(screen.getByText('Total Principal')).toBeDefined();
 expect(screen.getByText('Avg Yield')).toBeDefined();
 expect(screen.getByText('Avg Duration')).toBeDefined();
 expect(screen.getByText('Risk Score')).toBeDefined();
 // Values appear in both summary card and table - use getAllByText
 expect(screen.getAllByText('$150M').length).toBeGreaterThanOrEqual(1);
 expect(screen.getAllByText('$80M').length).toBeGreaterThanOrEqual(1);
 });

 it('shows winner indicators', () => {
 renderWithRouter(<PortfolioComparisonMode />);
 const winners = screen.getAllByText(/US|European/);
 expect(winners.length).toBeGreaterThan(0);
 });

 it('switches to allocation tab', () => {
 renderWithRouter(<PortfolioComparisonMode />);
 fireEvent.click(screen.getByText('allocation'));
 expect(screen.getByText('Currency Breakdown')).toBeDefined();
 expect(screen.getByText('Sector Breakdown')).toBeDefined();
 });

 it('switches to instruments tab', () => {
 renderWithRouter(<PortfolioComparisonMode />);
 fireEvent.click(screen.getByText('instruments'));
 expect(screen.getAllByText(/Top Instruments/).length).toBeGreaterThanOrEqual(1);
 });

 it('switches to risk tab and shows charts', () => {
 renderWithRouter(<PortfolioComparisonMode />);
 const riskBtns = screen.getAllByText('risk');
 fireEvent.click(riskBtns[0]);
 expect(screen.getAllByTestId('glass-bar-chart').length).toBeGreaterThanOrEqual(1);
 });

 it('shows portfolio summary values in summary cards', () => {
 renderWithRouter(<PortfolioComparisonMode />);
 // Summary card values have spaced text, table has combined - use getAllByText
 expect(screen.getAllByText(/4\.92/).length).toBeGreaterThanOrEqual(1);
 expect(screen.getAllByText(/3\.42/).length).toBeGreaterThanOrEqual(1);
 });
});
