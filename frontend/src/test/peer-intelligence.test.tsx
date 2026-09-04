import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import {
  MOCK_CONSENSUS_INDICATORS,
  MOCK_PEER_BENCHMARKS,
  MOCK_MARKET_SENTIMENT,
  MOCK_PEER_ACTIONS,
  getConsensusByCategory,
  getTopConsensus,
  getIncreasingTrends,
  getPercentileLabel,
  getPercentileColor,
  getSentimentColor,
  getSentimentIcon,
  getCategoryIcon,
  type ConsensusIndicator,
} from '../lib/peerIntelligence';
import PeerIntelligence from '../components/PeerIntelligence';

const renderWithRouter = (component: React.ReactNode) =>
  render(<BrowserRouter>{component}</BrowserRouter>);

// ── peerIntelligence Data Service Tests ───────────────────────────────

describe('peerIntelligence data service', () => {
  describe('MOCK_CONSENSUS_INDICATORS', () => {
    it('has 6 consensus indicators', () => {
      expect(MOCK_CONSENSUS_INDICATORS).toHaveLength(6);
    });

    it('each indicator has required fields', () => {
      MOCK_CONSENSUS_INDICATORS.forEach((c) => {
        expect(c.id).toBeTruthy();
        expect(c.title).toBeTruthy();
        expect(c.description).toBeTruthy();
        expect(c.consensusPercentage).toBeGreaterThan(0);
        expect(c.consensusPercentage).toBeLessThanOrEqual(100);
        expect(c.sampleSize).toBeGreaterThan(0);
        expect(c.confidence).toBeGreaterThan(0);
      });
    });

    it('spans multiple categories', () => {
      const cats = new Set(MOCK_CONSENSUS_INDICATORS.map((c) => c.category));
      expect(cats.size).toBeGreaterThanOrEqual(4);
    });

    it('all have valid trends', () => {
      MOCK_CONSENSUS_INDICATORS.forEach((c) => {
        expect(['increasing', 'decreasing', 'stable']).toContain(c.trend);
      });
    });
  });

  describe('MOCK_PEER_BENCHMARKS', () => {
    it('has 6 peer benchmarks', () => {
      expect(MOCK_PEER_BENCHMARKS).toHaveLength(6);
    });

    it('each benchmark has valid percentile', () => {
      MOCK_PEER_BENCHMARKS.forEach((b) => {
        expect(b.percentile).toBeGreaterThanOrEqual(0);
        expect(b.percentile).toBeLessThanOrEqual(100);
      });
    });

    it('peer ranges are ordered correctly', () => {
      MOCK_PEER_BENCHMARKS.forEach((b) => {
        expect(b.peerP10).toBeLessThan(b.peerP25);
        expect(b.peerP25).toBeLessThanOrEqual(b.peerMedian);
        expect(b.peerMedian).toBeLessThanOrEqual(b.peerP75);
        expect(b.peerP75).toBeLessThan(b.peerP90);
      });
    });
  });

  describe('MOCK_MARKET_SENTIMENT', () => {
    it('has 4 sentiment indicators', () => {
      expect(MOCK_MARKET_SENTIMENT).toHaveLength(4);
    });

    it('each sentiment has valid score', () => {
      MOCK_MARKET_SENTIMENT.forEach((s) => {
        expect(s.score).toBeGreaterThanOrEqual(-100);
        expect(s.score).toBeLessThanOrEqual(100);
      });
    });

    it('all have valid sentiment values', () => {
      MOCK_MARKET_SENTIMENT.forEach((s) => {
        expect(['bullish', 'bearish', 'neutral']).toContain(s.sentiment);
      });
    });
  });

  describe('MOCK_PEER_ACTIONS', () => {
    it('has 5 peer actions', () => {
      expect(MOCK_PEER_ACTIONS).toHaveLength(5);
    });

    it('each action has valid percentage', () => {
      MOCK_PEER_ACTIONS.forEach((a) => {
        expect(a.percentage).toBeGreaterThan(0);
        expect(a.percentage).toBeLessThanOrEqual(100);
      });
    });
  });

  describe('getConsensusByCategory', () => {
    it('filters by category', () => {
      const duration = getConsensusByCategory('duration');
      expect(duration.length).toBeGreaterThan(0);
      duration.forEach((c) => expect(c.category).toBe('duration'));
    });

    it('returns empty for non-existent category', () => {
      const result = getConsensusByCategory('nonexistent' as ConsensusIndicator['category']);
      expect(result).toHaveLength(0);
    });
  });

  describe('getTopConsensus', () => {
    it('returns top N by consensus percentage', () => {
      const top3 = getTopConsensus(3);
      expect(top3).toHaveLength(3);
      expect(top3[0].consensusPercentage).toBeGreaterThanOrEqual(top3[1].consensusPercentage);
      expect(top3[1].consensusPercentage).toBeGreaterThanOrEqual(top3[2].consensusPercentage);
    });
  });

  describe('getIncreasingTrends', () => {
    it('returns only increasing indicators', () => {
      const increasing = getIncreasingTrends();
      expect(increasing.length).toBeGreaterThan(0);
      increasing.forEach((c) => expect(c.trend).toBe('increasing'));
    });
  });

  describe('getPercentileLabel', () => {
    it('returns correct labels', () => {
      expect(getPercentileLabel(95)).toBe('Top 10%');
      expect(getPercentileLabel(80)).toBe('Top 25%');
      expect(getPercentileLabel(60)).toBe('Above Median');
      expect(getPercentileLabel(30)).toBe('Below Median');
      expect(getPercentileLabel(10)).toBe('Bottom 25%');
    });
  });

  describe('getPercentileColor', () => {
    it('returns different colors for different percentiles', () => {
      const p90 = getPercentileColor(90);
      const p60 = getPercentileColor(60);
      const p30 = getPercentileColor(30);
      expect(p90).not.toBe(p60);
      expect(p60).not.toBe(p30);
    });
  });

  describe('getSentimentColor', () => {
    it('returns colors for each sentiment', () => {
      expect(getSentimentColor('bullish')).toContain('emerald');
      expect(getSentimentColor('bearish')).toContain('red');
      expect(getSentimentColor('neutral')).toContain('slate');
    });
  });

  describe('getSentimentIcon', () => {
    it('returns icons for each sentiment', () => {
      expect(getSentimentIcon('bullish')).toBeTruthy();
      expect(getSentimentIcon('bearish')).toBeTruthy();
      expect(getSentimentIcon('neutral')).toBeTruthy();
    });
  });

  describe('getCategoryIcon', () => {
    it('returns icons for all categories', () => {
      expect(getCategoryIcon('duration')).toBeTruthy();
      expect(getCategoryIcon('allocation')).toBeTruthy();
      expect(getCategoryIcon('hedging')).toBeTruthy();
      expect(getCategoryIcon('credit')).toBeTruthy();
      expect(getCategoryIcon('refinancing')).toBeTruthy();
      expect(getCategoryIcon('risk')).toBeTruthy();
    });
  });
});

// ── PeerIntelligence Component Tests ──────────────────────────────────

describe('PeerIntelligence', () => {
  it('renders page title', () => {
    renderWithRouter(<PeerIntelligence />);
    expect(screen.getByText('Peer Intelligence')).toBeDefined();
  });

  it('renders sample size info', () => {
    renderWithRouter(<PeerIntelligence />);
    const portfolios = screen.getAllByText(/portfolios/);
    expect(portfolios.length).toBeGreaterThan(0);
  });

  it('shows quick stats cards', () => {
    renderWithRouter(<PeerIntelligence />);
    expect(screen.getByText('Top Consensus')).toBeDefined();
    expect(screen.getByText('Bullish Signals')).toBeDefined();
    expect(screen.getByText('Above Median')).toBeDefined();
    expect(screen.getByText('Popular Actions')).toBeDefined();
  });

  it('renders tab buttons', () => {
    renderWithRouter(<PeerIntelligence />);
    const consensus = screen.getAllByText(/Consensus/);
    expect(consensus.length).toBeGreaterThan(0);
    const benchmarks = screen.getAllByText(/Benchmarks/);
    expect(benchmarks.length).toBeGreaterThan(0);
  });

  it('shows consensus indicators on default tab', () => {
    renderWithRouter(<PeerIntelligence />);
    expect(screen.getByText('Extending Duration')).toBeDefined();
    expect(screen.getByText('Adding FX Hedges')).toBeDefined();
    expect(screen.getByText('Green Bond Allocation')).toBeDefined();
  });

  it('shows category filter buttons', () => {
    renderWithRouter(<PeerIntelligence />);
    const allBtn = screen.getAllByText('All');
    expect(allBtn.length).toBeGreaterThan(0);
    const duration = screen.getAllByText(/Duration/);
    expect(duration.length).toBeGreaterThan(0);
  });

  it('shows actionable badges', () => {
    renderWithRouter(<PeerIntelligence />);
    const badges = screen.getAllByText('Actionable');
    expect(badges.length).toBeGreaterThan(0);
  });
});
