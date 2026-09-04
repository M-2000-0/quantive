import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import ConsensusAlert from '../components/ConsensusAlert';
import PeerAlignmentTracker from '../components/PeerAlignmentTracker';
import MonthlyPeerReport from '../components/MonthlyPeerReport';
import { MOCK_MARKET_SENTIMENT, getSentimentColor, getSentimentIcon } from '../lib/peerIntelligence';

const renderWithRouter = (component: React.ReactNode) =>
  render(<BrowserRouter>{component}</BrowserRouter>);

// ── ConsensusAlert Tests ──────────────────────────────────────────────

describe('ConsensusAlert', () => {
  it('renders nothing when disabled', () => {
    const { container } = renderWithRouter(<ConsensusAlert enabled={false} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders alerts when above threshold', () => {
    renderWithRouter(<ConsensusAlert threshold={60} />);
    const alerts = screen.getAllByText(/%/);
    expect(alerts.length).toBeGreaterThan(0);
  });

  it('shows alert title', () => {
    renderWithRouter(<ConsensusAlert threshold={60} />);
    const extending = screen.getAllByText(/Extending Duration/);
    expect(extending.length).toBeGreaterThan(0);
  });

  it('shows Peer Consensus Alerts header', () => {
    renderWithRouter(<ConsensusAlert threshold={60} />);
    expect(screen.getByText('Peer Consensus Alerts')).toBeDefined();
  });

  it('respects maxAlerts limit', () => {
    renderWithRouter(<ConsensusAlert threshold={50} maxAlerts={2} />);
    // Should show at most 2 alerts
    const dismissButtons = screen.getAllByText('✕');
    expect(dismissButtons.length).toBeLessThanOrEqual(3); // 2 alerts + header
  });

  it('shows sample size and confidence', () => {
    renderWithRouter(<ConsensusAlert threshold={60} />);
    const portfolios = screen.getAllByText(/portfolios/);
    expect(portfolios.length).toBeGreaterThan(0);
    const confidence = screen.getAllByText(/confidence/);
    expect(confidence.length).toBeGreaterThan(0);
  });

  it('shows actionable badges', () => {
    renderWithRouter(<ConsensusAlert threshold={60} />);
    // Actionable badges are rendered as uppercase text
    const badges = document.querySelectorAll('[class*="uppercase"]');
    expect(badges.length).toBeGreaterThan(0);
  });
});

// ── PeerAlignmentTracker Tests ────────────────────────────────────────

describe('PeerAlignmentTracker', () => {
  it('renders header', () => {
    renderWithRouter(<PeerAlignmentTracker />);
    expect(screen.getByText('Peer Alignment')).toBeDefined();
  });

  it('shows overall alignment score', () => {
    renderWithRouter(<PeerAlignmentTracker />);
    expect(screen.getByText(/Overall Alignment/)).toBeDefined();
  });

  it('shows dimension labels', () => {
    renderWithRouter(<PeerAlignmentTracker />);
    expect(screen.getByText('Duration')).toBeDefined();
    expect(screen.getByText('FX Hedging')).toBeDefined();
    expect(screen.getByText('Credit Exposure')).toBeDefined();
    expect(screen.getByText('Green Bonds')).toBeDefined();
  });

  it('shows alignment percentages', () => {
    renderWithRouter(<PeerAlignmentTracker />);
    const percentages = screen.getAllByText(/%/);
    expect(percentages.length).toBeGreaterThan(0);
  });

  it('shows trend badges', () => {
    renderWithRouter(<PeerAlignmentTracker />);
    const aligned = screen.getAllByText(/Aligned/);
    expect(aligned.length).toBeGreaterThan(0);
  });

  it('shows insight text', () => {
    renderWithRouter(<PeerAlignmentTracker />);
    const insights = screen.getAllByText(/duration|hedging|exposure|allocation/i);
    expect(insights.length).toBeGreaterThan(0);
  });

  it('accepts custom props', () => {
    renderWithRouter(
      <PeerAlignmentTracker
        portfolioDuration={6.0}
        fxHedgeRatio={90}
        hyExposure={30}
        greenBondPct={20}
      />
    );
    expect(screen.getByText('Peer Alignment')).toBeDefined();
  });
});

// ── MonthlyPeerReport Tests ───────────────────────────────────────────

describe('MonthlyPeerReport', () => {
  it('renders report header', () => {
    renderWithRouter(<MonthlyPeerReport />);
    expect(screen.getByText(/Monthly Peer Intelligence Report/)).toBeDefined();
  });

  it('shows executive summary stats', () => {
    renderWithRouter(<MonthlyPeerReport />);
    expect(screen.getByText('Consensus trends tracked')).toBeDefined();
    expect(screen.getByText('Trends increasing this month')).toBeDefined();
    expect(screen.getByText(/Your metrics above median/)).toBeDefined();
  });

  it('shows collapsible sections', () => {
    renderWithRouter(<MonthlyPeerReport />);
    expect(screen.getByText('Consensus Shifts')).toBeDefined();
    expect(screen.getByText('Benchmark Changes')).toBeDefined();
    expect(screen.getByText('Sentiment Evolution')).toBeDefined();
    expect(screen.getByText('Top Peer Actions')).toBeDefined();
  });

  it('shows disclaimer', () => {
    renderWithRouter(<MonthlyPeerReport />);
    expect(screen.getByText(/does not constitute investment advice/)).toBeDefined();
  });

  it('accepts custom month', () => {
    renderWithRouter(<MonthlyPeerReport month="January 2027" />);
    const month = screen.getAllByText(/January 2027/);
    expect(month.length).toBeGreaterThan(0);
  });

  it('summary section is expanded by default', () => {
    renderWithRouter(<MonthlyPeerReport />);
    // Executive Summary content should be visible
    expect(screen.getByText(/Consensus trends tracked/)).toBeDefined();
  });
});

// ── Peer Sentiment Integration Tests ──────────────────────────────────

describe('peer sentiment data', () => {
  it('has 4 sentiment indicators', () => {
    expect(MOCK_MARKET_SENTIMENT).toHaveLength(4);
  });

  it('sentiment colors are valid', () => {
    MOCK_MARKET_SENTIMENT.forEach((s) => {
      const color = getSentimentColor(s.sentiment);
      expect(color).toBeTruthy();
      expect(color).toContain('text-');
    });
  });

  it('sentiment icons are valid', () => {
    MOCK_MARKET_SENTIMENT.forEach((s) => {
      const icon = getSentimentIcon(s.sentiment);
      expect(icon).toBeTruthy();
    });
  });
});
