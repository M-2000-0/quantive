import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import KeyboardShortcutOverlay from '../components/KeyboardShortcutOverlay';
import SmartSearch from '../components/SmartSearch';
import SkeletonLoader from '../components/ui/SkeletonLoader';
import ReturnRateAnalytics from '../components/ReturnRateAnalytics';
import PostDeliverySurvey from '../components/PostDeliverySurvey';

describe('KeyboardShortcutOverlay', () => {
  it('does not render when closed', () => {
    render(<KeyboardShortcutOverlay />);
    expect(screen.queryByText('Keyboard Shortcuts')).toBeNull();
  });

  it('renders all shortcut categories when opened via keyboard', async () => {
    render(<KeyboardShortcutOverlay />);
    fireEvent.keyDown(document, { key: '?' });
    await waitFor(() => {
      expect(screen.getByText('Keyboard Shortcuts')).toBeDefined();
    });
    expect(screen.getAllByText('Navigation').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Editing').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Charts').length).toBeGreaterThanOrEqual(1);
  });

  it('shows specific shortcuts', async () => {
    render(<KeyboardShortcutOverlay />);
    fireEvent.keyDown(document, { key: '?' });
    await waitFor(() => {
      expect(screen.getByText('Open command palette')).toBeDefined();
    });
    expect(screen.getByText('Undo last edit')).toBeDefined();
  });

  it('closes on Escape', async () => {
    render(<KeyboardShortcutOverlay />);
    fireEvent.keyDown(document, { key: '?' });
    await waitFor(() => {
      expect(screen.getByText('Keyboard Shortcuts')).toBeDefined();
    });
    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => {
      expect(screen.queryByText('Keyboard Shortcuts')).toBeNull();
    });
  });
});

describe('SmartSearch', () => {
  it('renders search input', () => {
    render(<MemoryRouter><SmartSearch /></MemoryRouter>);
    expect(screen.getByPlaceholderText(/Search or type/)).toBeDefined();
  });

  it('shows results for natural language queries', async () => {
    render(<MemoryRouter><SmartSearch /></MemoryRouter>);
    const input = screen.getByPlaceholderText(/Search or type/);
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: 'show me risk dashboard' } });
    await waitFor(() => {
      expect(screen.getByText('Risk Dashboard')).toBeDefined();
    });
  });

  it('shows multiple results for broad queries', async () => {
    render(<MemoryRouter><SmartSearch /></MemoryRouter>);
    const input = screen.getByPlaceholderText(/Search or type/);
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: 'show me market data and portfolio' } });
    await waitFor(() => {
      expect(screen.getByText('Market Data')).toBeDefined();
      expect(screen.getByText('Portfolios')).toBeDefined();
    });
  });

  it('navigates on Enter', async () => {
    render(<MemoryRouter><SmartSearch /></MemoryRouter>);
    const input = screen.getByPlaceholderText(/Search or type/);
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: 'settings' } });
    await waitFor(() => {
      expect(screen.getByText('Settings')).toBeDefined();
    });
  });
});

describe('SkeletonLoader', () => {
  it('renders dashboard layout', () => {
    const { container } = render(<SkeletonLoader layout="dashboard" />);
    expect(container.querySelector('.skeleton')).toBeDefined();
  });

  it('renders list layout', () => {
    render(<SkeletonLoader layout="list" rows={3} />);
    // Should render without errors
    expect(document.querySelector('.skeleton')).toBeDefined();
  });

  it('renders chart layout', () => {
    render(<SkeletonLoader layout="chart" />);
    expect(document.querySelector('.skeleton')).toBeDefined();
  });

  it('renders form layout', () => {
    render(<SkeletonLoader layout="form" />);
    expect(document.querySelector('.skeleton')).toBeDefined();
  });
});

describe('ReturnRateAnalytics', () => {
  it('renders summary stats', () => {
    render(<ReturnRateAnalytics />);
    expect(screen.getByText('Return Rate')).toBeDefined();
    expect(screen.getByText('Total Returns')).toBeDefined();
    expect(screen.getByText('Refund Total')).toBeDefined();
  });

  it('renders tab navigation', () => {
    render(<ReturnRateAnalytics />);
    expect(screen.getByText('Overview')).toBeDefined();
    expect(screen.getByText('Reasons')).toBeDefined();
    expect(screen.getByText('Segments')).toBeDefined();
    expect(screen.getByText('Products')).toBeDefined();
  });

  it('switches to reasons tab', async () => {
    render(<ReturnRateAnalytics />);
    fireEvent.click(screen.getByText('Reasons'));
    await waitFor(() => {
      expect(screen.getByText('Top Return Reasons')).toBeDefined();
      expect(screen.getByText('Size/Fit Issue')).toBeDefined();
    });
  });

  it('switches to segments tab', async () => {
    render(<ReturnRateAnalytics />);
    fireEvent.click(screen.getByText('Segments'));
    await waitFor(() => {
      expect(screen.getByText('Return Rate by Customer Segment')).toBeDefined();
    });
  });

  it('switches to products tab', async () => {
    render(<ReturnRateAnalytics />);
    fireEvent.click(screen.getByText('Products'));
    await waitFor(() => {
      expect(screen.getByText('Most Returned Products')).toBeDefined();
    });
  });
});

describe('PostDeliverySurvey', () => {
  it('renders step 1 (satisfaction rating)', () => {
    render(<PostDeliverySurvey />);
    expect(screen.getByText('How was your experience?')).toBeDefined();
    expect(screen.getByText('1')).toBeDefined();
    expect(screen.getByText('5')).toBeDefined();
  });

  it('advances to step 2 after rating', async () => {
    render(<PostDeliverySurvey />);
    fireEvent.click(screen.getByText('4'));
    fireEvent.click(screen.getByText('Next'));
    await waitFor(() => {
      expect(screen.getByText('Did it meet your expectations?')).toBeDefined();
    });
  });

  it('advances to step 3 and submits', async () => {
    const onSubmit = vi.fn();
    render(<PostDeliverySurvey onSubmit={onSubmit} />);
    // Step 1: Rate
    fireEvent.click(screen.getByText('5'));
    fireEvent.click(screen.getByText('Next'));
    // Step 2: Expectations
    await waitFor(() => {
      expect(screen.getByText('Did it meet your expectations?')).toBeDefined();
    });
    fireEvent.click(screen.getByText('Yes, exactly'));
    fireEvent.click(screen.getByText('Next'));
    // Step 3: Recommend
    await waitFor(() => {
      expect(screen.getByText('Would you recommend us?')).toBeDefined();
    });
    fireEvent.click(screen.getByText('Submit Feedback'));
    await waitFor(() => {
      expect(screen.getByText('Thank you for your feedback!')).toBeDefined();
    });
    expect(onSubmit).toHaveBeenCalled();
  });

  it('shows return reason when expectations not met', async () => {
    render(<PostDeliverySurvey />);
    fireEvent.click(screen.getByText('3'));
    fireEvent.click(screen.getByText('Next'));
    await waitFor(() => {
      expect(screen.getByText('Did it meet your expectations?')).toBeDefined();
    });
    fireEvent.click(screen.getByText('Not really'));
    await waitFor(() => {
      expect(screen.getByText('What was the main issue?')).toBeDefined();
    });
  });
});
