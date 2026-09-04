import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import EngagementAnalytics from '../components/EngagementAnalytics';
import GuidedTour from '../components/GuidedTour';
import ThemeTransition from '../components/ThemeTransition';
import NotificationCenter from '../components/NotificationCenter';

describe('EngagementAnalytics', () => {
  it('renders summary stats', () => {
    render(<EngagementAnalytics />);
    expect(screen.getByText('Total Page Views')).toBeDefined();
    expect(screen.getByText('Unique Users')).toBeDefined();
    expect(screen.getByText('Avg Bounce Rate')).toBeDefined();
  });

  it('renders tab navigation', () => {
    render(<EngagementAnalytics />);
    expect(screen.getByText('Overview')).toBeDefined();
    expect(screen.getByText('Pages')).toBeDefined();
    expect(screen.getByText('Features')).toBeDefined();
    expect(screen.getByText('Sessions')).toBeDefined();
  });

  it('switches to pages tab', async () => {
    render(<EngagementAnalytics />);
    fireEvent.click(screen.getByText('Pages'));
    await waitFor(() => {
      expect(screen.getByText('/dashboard')).toBeDefined();
      expect(screen.getByText('/portfolios')).toBeDefined();
    });
  });

  it('switches to features tab', async () => {
    render(<EngagementAnalytics />);
    fireEvent.click(screen.getByText('Features'));
    await waitFor(() => {
      expect(screen.getByText('Run Optimization')).toBeDefined();
      expect(screen.getByText('Export Report')).toBeDefined();
    });
  });

  it('switches to sessions tab', async () => {
    render(<EngagementAnalytics />);
    fireEvent.click(screen.getByText('Sessions'));
    await waitFor(() => {
      expect(screen.getByText('Daily Sessions')).toBeDefined();
      expect(screen.getByText('Session Duration Distribution')).toBeDefined();
    });
  });

  it('changes date range', async () => {
    render(<EngagementAnalytics />);
    fireEvent.click(screen.getByText('30d'));
    // Should still render without errors
    expect(screen.getByText('Total Page Views')).toBeDefined();
  });
});

describe('GuidedTour', () => {
  it('does not render when not active', () => {
    // Clear any previous completion state
    localStorage.removeItem('quantive_tour_test');
    render(<GuidedTour storageKey="quantive_tour_test" />);
    expect(screen.queryByText('Navigation Sidebar')).toBeNull();
  });

  it('renders tour steps when activated', async () => {
    localStorage.removeItem('quantive_tour_test');
    // Create a target element
    const div = document.createElement('div');
    div.setAttribute('data-tour', 'sidebar');
    document.body.appendChild(div);

    render(<GuidedTour storageKey="quantive_tour_test" />);
    // Tour auto-starts after 1.5s
    await waitFor(() => {
      expect(screen.getByText('Navigation Sidebar')).toBeDefined();
    }, { timeout: 3000 });

    document.body.removeChild(div);
  });

  it('shows progress indicator', async () => {
    localStorage.removeItem('quantive_tour_progress');
    const div = document.createElement('div');
    div.setAttribute('data-tour', 'sidebar');
    document.body.appendChild(div);

    render(<GuidedTour storageKey="quantive_tour_progress" steps={[
      { target: '[data-tour="sidebar"]', title: 'Step 1', content: 'Content 1' },
      { target: '[data-tour="sidebar"]', title: 'Step 2', content: 'Content 2' },
    ]} />);

    await waitFor(() => {
      expect(screen.getByText('1 of 2')).toBeDefined();
    }, { timeout: 3000 });

    document.body.removeChild(div);
  });
});

describe('ThemeTransition', () => {
  it('renders theme button', () => {
    render(<MemoryRouter><ThemeTransition /></MemoryRouter>);
    expect(screen.getByText('Light')).toBeDefined();
  });

  it('opens theme picker on click', async () => {
    render(<MemoryRouter><ThemeTransition /></MemoryRouter>);
    fireEvent.click(screen.getByText('Light'));
    await waitFor(() => {
      expect(screen.getByText('Choose Theme')).toBeDefined();
    });
  });

  it('shows all theme options', async () => {
    render(<MemoryRouter><ThemeTransition /></MemoryRouter>);
    fireEvent.click(screen.getByText('Light'));
    await waitFor(() => {
      expect(screen.getByText('Choose Theme')).toBeDefined();
    });
    expect(screen.getByText('Dark')).toBeDefined();
    expect(screen.getByText('Ocean')).toBeDefined();
    expect(screen.getByText('Forest')).toBeDefined();
    expect(screen.getByText('Sunset')).toBeDefined();
    expect(screen.getByText('System')).toBeDefined();
  });

  it('selects a theme', async () => {
    const onChange = vi.fn();
    render(<MemoryRouter><ThemeTransition onThemeChange={onChange} /></MemoryRouter>);
    fireEvent.click(screen.getByText('Light'));
    await waitFor(() => {
      expect(screen.getByText('Choose Theme')).toBeDefined();
    });
    fireEvent.click(screen.getByText('Dark'));
    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith('dark');
    });
  });
});

describe('NotificationCenter', () => {
  it('renders bell icon', () => {
    render(<MemoryRouter><NotificationCenter /></MemoryRouter>);
    // The bell SVG is rendered
    expect(screen.getByTitle('Notifications')).toBeDefined();
  });

  it('shows unread count badge', () => {
    render(<MemoryRouter><NotificationCenter /></MemoryRouter>);
    expect(screen.getByText('3')).toBeDefined(); // 3 unread notifications
  });

  it('opens dropdown on click', async () => {
    render(<MemoryRouter><NotificationCenter /></MemoryRouter>);
    fireEvent.click(screen.getByTitle('Notifications'));
    await waitFor(() => {
      expect(screen.getByText('Notifications')).toBeDefined();
      expect(screen.getByText(/unread/)).toBeDefined();
    });
  });

  it('shows notification list', async () => {
    render(<MemoryRouter><NotificationCenter /></MemoryRouter>);
    fireEvent.click(screen.getByTitle('Notifications'));
    await waitFor(() => {
      expect(screen.getByText('Optimization Complete')).toBeDefined();
      expect(screen.getByText('Duration Mismatch Detected')).toBeDefined();
    });
  });

  it('has category filters', async () => {
    render(<MemoryRouter><NotificationCenter /></MemoryRouter>);
    fireEvent.click(screen.getByTitle('Notifications'));
    await waitFor(() => {
      expect(screen.getByText('All')).toBeDefined();
      expect(screen.getByText('Optimization')).toBeDefined();
      expect(screen.getByText('Risk')).toBeDefined();
      expect(screen.getByText('Team')).toBeDefined();
      expect(screen.getByText('System')).toBeDefined();
    });
  });

  it('marks all as read', async () => {
    render(<MemoryRouter><NotificationCenter /></MemoryRouter>);
    fireEvent.click(screen.getByTitle('Notifications'));
    await waitFor(() => {
      expect(screen.getByText('Mark all read')).toBeDefined();
    });
    fireEvent.click(screen.getByText('Mark all read'));
    await waitFor(() => {
      expect(screen.queryByText('Mark all read')).toBeNull();
    });
  });

  it('filters by category', async () => {
    render(<MemoryRouter><NotificationCenter /></MemoryRouter>);
    fireEvent.click(screen.getByTitle('Notifications'));
    await waitFor(() => {
      expect(screen.getByText('Optimization Complete')).toBeDefined();
    });
    // Click Risk tab
    fireEvent.click(screen.getByText('Risk'));
    await waitFor(() => {
      expect(screen.getByText('Duration Mismatch Detected')).toBeDefined();
      expect(screen.queryByText('Optimization Complete')).toBeNull();
    });
  });

  it('shows empty state when all cleared', async () => {
    render(<MemoryRouter><NotificationCenter /></MemoryRouter>);
    fireEvent.click(screen.getByTitle('Notifications'));
    await waitFor(() => {
      expect(screen.getByText('Clear all')).toBeDefined();
    });
    fireEvent.click(screen.getByText('Clear all'));
    await waitFor(() => {
      expect(screen.getByText('All caught up!')).toBeDefined();
    });
  });
});
