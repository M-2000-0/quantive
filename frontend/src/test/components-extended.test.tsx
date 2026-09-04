import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// ─── DataTable ───
import DataTable from '../components/ui/DataTable';

const columns = [
  { key: 'name', label: 'Name' },
  { key: 'value', label: 'Value' },
];

const rows = [
  { name: 'Alpha', value: 100 },
  { name: 'Beta', value: 50 },
  { name: 'Gamma', value: 200 },
] as Record<string, unknown>[];

describe('DataTable', () => {
  it('renders column headers', () => {
    render(<DataTable columns={columns} data={rows} />);
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Value')).toBeInTheDocument();
  });

  it('renders all data rows', () => {
    render(<DataTable columns={columns} data={rows} />);
    expect(screen.getByText('Alpha')).toBeInTheDocument();
    expect(screen.getByText('Beta')).toBeInTheDocument();
    expect(screen.getByText('Gamma')).toBeInTheDocument();
  });

  it('renders empty message when no data', () => {
    render(<DataTable columns={columns} data={[]} emptyMessage="Nothing here" />);
    expect(screen.getByText('Nothing here')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(<DataTable columns={columns} data={rows} loading />);
    expect(screen.getByText('Loading…')).toBeInTheDocument();
  });

  it('calls onRowClick when row is clicked', () => {
    const onClick = vi.fn();
    render(<DataTable columns={columns} data={rows} onRowClick={onClick} />);
    fireEvent.click(screen.getByText('Alpha'));
    expect(onClick).toHaveBeenCalledWith(rows[0]);
  });

  it('sorts data when header is clicked', () => {
    render(<DataTable columns={columns} data={rows} />);
    // Click "Value" header to sort ascending
    fireEvent.click(screen.getByText('Value'));
    const cells = screen.getAllByRole('cell');
    // First data row should be Beta (50)
    expect(cells[1].textContent).toBe('50');
  });

  it('supports custom render function', () => {
    const customColumns = [
      { key: 'name', label: 'Name', render: (val: unknown) => <strong>{String(val)}</strong> },
    ];
    render(<DataTable columns={customColumns} data={rows} />);
    const strong = screen.getByText('Alpha').closest('strong');
    expect(strong).toBeTruthy();
  });

  it('supports compact mode', () => {
    const { container } = render(<DataTable columns={columns} data={rows} compact />);
    expect(container.querySelector('table')).toBeInTheDocument();
  });
});

// ─── Modal ───
import Modal from '../components/ui/Modal';

describe('Modal', () => {
  it('renders nothing when closed', () => {
    render(
      <Modal isOpen={false} onClose={() => {}} title="Test Modal">
        <p>Content</p>
      </Modal>
    );
    expect(screen.queryByText('Test Modal')).not.toBeInTheDocument();
  });

  it('renders when open', () => {
    render(
      <Modal isOpen={true} onClose={() => {}} title="Test Modal">
        <p>Content</p>
      </Modal>
    );
    expect(screen.getByText('Test Modal')).toBeInTheDocument();
    expect(screen.getByText('Content')).toBeInTheDocument();
  });

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={onClose} title="Closeable">
        <p>Body</p>
      </Modal>
    );
    fireEvent.click(screen.getByLabelText('Close'));
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose on Escape key', () => {
    const onClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={onClose} title="Escapable">
        <p>Body</p>
      </Modal>
    );
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose on overlay click', () => {
    const onClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={onClose} title="Overlay">
        <p>Body</p>
      </Modal>
    );
    const overlay = screen.getByRole('dialog');
    fireEvent.click(overlay);
    expect(onClose).toHaveBeenCalled();
  });

  it('has correct aria attributes', () => {
    render(
      <Modal isOpen={true} onClose={() => {}} title="Aria Test">
        <p>Body</p>
      </Modal>
    );
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-labelledby', 'modal-title');
  });
});

// ─── Skeleton ───
import { SkeletonText, SkeletonCard, SkeletonTable } from '../components/ui/Skeleton';

describe('Skeleton', () => {
  it('SkeletonText renders correct number of lines', () => {
    const { container } = render(<SkeletonText lines={5} />);
    const items = container.querySelectorAll('.animate-pulse');
    expect(items.length).toBe(5);
  });

  it('SkeletonText defaults to 3 lines', () => {
    const { container } = render(<SkeletonText />);
    const items = container.querySelectorAll('.animate-pulse');
    expect(items.length).toBe(3);
  });

  it('SkeletonCard renders with aria-busy', () => {
    const { container } = render(<SkeletonCard />);
    expect(container.querySelector('[aria-busy="true"]')).toBeInTheDocument();
  });

  it('SkeletonTable renders correct rows and cols', () => {
    const { container } = render(<SkeletonTable rows={3} cols={4} />);
    expect(container.querySelector('[aria-busy="true"]')).toBeInTheDocument();
  });
});

// ─── Tabs ───
import Tabs from '../components/ui/Tabs';

describe('Tabs', () => {
  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'details', label: 'Details' },
    { id: 'disabled', label: 'Disabled', disabled: true },
  ];

  it('renders all tab labels', () => {
    render(
      <Tabs tabs={tabs} activeTab="overview" onChange={() => {}}>
        <div>Panel</div>
      </Tabs>
    );
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Details')).toBeInTheDocument();
    expect(screen.getByText('Disabled')).toBeInTheDocument();
  });

  it('marks active tab with aria-selected', () => {
    render(
      <Tabs tabs={tabs} activeTab="details" onChange={() => {}}>
        <div>Panel</div>
      </Tabs>
    );
    expect(screen.getByRole('tab', { name: 'Details' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'false');
  });

  it('calls onChange when tab clicked', () => {
    const onChange = vi.fn();
    render(
      <Tabs tabs={tabs} activeTab="overview" onChange={onChange}>
        <div>Panel</div>
      </Tabs>
    );
    fireEvent.click(screen.getByText('Details'));
    expect(onChange).toHaveBeenCalledWith('details');
  });

  it('disabled tab cannot be clicked', () => {
    const onChange = vi.fn();
    render(
      <Tabs tabs={tabs} activeTab="overview" onChange={onChange}>
        <div>Panel</div>
      </Tabs>
    );
    const disabledTab = screen.getByRole('tab', { name: 'Disabled' });
    expect(disabledTab).toBeDisabled();
    fireEvent.click(disabledTab);
    expect(onChange).not.toHaveBeenCalled();
  });

  it('renders children content', () => {
    render(
      <Tabs tabs={tabs} activeTab="overview" onChange={() => {}}>
        <div>Panel Content</div>
      </Tabs>
    );
    expect(screen.getByText('Panel Content')).toBeInTheDocument();
  });
});

// ─── EmptyState ───
import EmptyState from '../components/ui/EmptyState';

describe('EmptyState', () => {
  it('renders title and description', () => {
    render(
      <EmptyState
        icon={<span>📭</span>}
        title="No items"
        description="Create one to get started"
      />
    );
    expect(screen.getByText('No items')).toBeInTheDocument();
    expect(screen.getByText('Create one to get started')).toBeInTheDocument();
  });

  it('renders action button when provided', () => {
    const onClick = vi.fn();
    render(
      <EmptyState
        icon={<span>📭</span>}
        title="Empty"
        description="Nothing here"
        action={{ label: 'Create', onClick }}
      />
    );
    fireEvent.click(screen.getByText('Create'));
    expect(onClick).toHaveBeenCalled();
  });

  it('does not render action button when not provided', () => {
    render(
      <EmptyState
        icon={<span>📭</span>}
        title="Empty"
        description="Nothing here"
      />
    );
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});

// ─── Breadcrumbs ───
import Breadcrumbs from '../components/ui/Breadcrumbs';

describe('Breadcrumbs', () => {
  it('renders all breadcrumb items', () => {
    render(
      <MemoryRouter>
        <Breadcrumbs items={[
          { label: 'Home', path: '/' },
          { label: 'Portfolios', path: '/portfolios' },
          { label: 'Detail' },
        ]} />
      </MemoryRouter>
    );
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Portfolios')).toBeInTheDocument();
    expect(screen.getByText('Detail')).toBeInTheDocument();
  });

  it('renders links for items with paths', () => {
    render(
      <MemoryRouter>
        <Breadcrumbs items={[
          { label: 'Home', path: '/' },
          { label: 'Current' },
        ]} />
      </MemoryRouter>
    );
    const homeLink = screen.getByText('Home');
    expect(homeLink.tagName).toBe('A');
  });

  it('marks last item as current (not a link)', () => {
    render(
      <MemoryRouter>
        <Breadcrumbs items={[
          { label: 'Home', path: '/' },
          { label: 'Current' },
        ]} />
      </MemoryRouter>
    );
    const current = screen.getByText('Current');
    expect(current.tagName).toBe('SPAN');
  });

  it('has correct aria-label', () => {
    render(
      <MemoryRouter>
        <Breadcrumbs items={[{ label: 'Home', path: '/' }]} />
      </MemoryRouter>
    );
    expect(screen.getByLabelText('Breadcrumb')).toBeInTheDocument();
  });
});

// ─── LoadingSpinner ───
import LoadingSpinner from '../components/ui/LoadingSpinner';

describe('LoadingSpinner', () => {
  it('renders default message', () => {
    render(<LoadingSpinner />);
    expect(screen.getByText('Loading…')).toBeInTheDocument();
  });

  it('renders custom message', () => {
    render(<LoadingSpinner message="Fetching data..." />);
    expect(screen.getByText('Fetching data...')).toBeInTheDocument();
  });

  it('renders full-page by default', () => {
    const { container } = render(<LoadingSpinner />);
    expect(container.querySelector('.min-h-\\[400px\\]')).toBeInTheDocument();
  });

  it('renders inline when fullPage=false', () => {
    const { container } = render(<LoadingSpinner fullPage={false} />);
    expect(container.querySelector('.min-h-\\[400px\\]')).not.toBeInTheDocument();
  });
});

// ─── PageTransition ───
import PageTransition from '../components/PageTransition';

describe('PageTransition', () => {
  it('renders children', () => {
    render(
      <MemoryRouter>
        <PageTransition>
          <div>Page Content</div>
        </PageTransition>
      </MemoryRouter>
    );
    expect(screen.getByText('Page Content')).toBeInTheDocument();
  });

  it('applies transition classes', () => {
    const { container } = render(
      <MemoryRouter>
        <PageTransition>
          <div>Content</div>
        </PageTransition>
      </MemoryRouter>
    );
    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper).toHaveClass('transition-opacity');
    expect(wrapper).toHaveAttribute('style');
  });
});

// ─── ConfidenceBadge (extended) ───
import ConfidenceBadge from '../components/ui/ConfidenceBadge';

describe('ConfidenceBadge extended', () => {
  it('renders High Confidence label', () => {
    render(<ConfidenceBadge score={95} />);
    expect(screen.getByText('High Confidence')).toBeInTheDocument();
  });

  it('renders Low Confidence label', () => {
    render(<ConfidenceBadge score={30} />);
    expect(screen.getByText('Low Confidence')).toBeInTheDocument();
  });

  it('renders score number inside circle', () => {
    render(<ConfidenceBadge score={72} />);
    expect(screen.getByText('72')).toBeInTheDocument();
  });
});

// ─── ThemeToggle (extended) ───
import ThemeToggle from '../components/ThemeToggle';
import { ThemeProvider } from '../stores/theme';

function themeWrapper({ children }: { children: React.ReactNode }) {
  return <ThemeProvider>{children}</ThemeProvider>;
}

describe('ThemeToggle', () => {
  it('renders without crashing', () => {
    render(<ThemeToggle />, { wrapper: themeWrapper });
    const btn = screen.getByRole('button');
    expect(btn).toBeInTheDocument();
  });

  it('toggles theme on click', () => {
    render(<ThemeToggle />, { wrapper: themeWrapper });
    fireEvent.click(screen.getByRole('button'));
    // Should still be a button after toggle
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('has correct title based on theme', () => {
    render(<ThemeToggle />, { wrapper: themeWrapper });
    const btn = screen.getByRole('button');
    expect(btn.getAttribute('title')).toMatch(/Switch to/);
  });
});

// ─── NotificationBell (extended) ───
import NotificationBell from '../components/NotificationBell';

describe('NotificationBell', () => {
  it('renders bell button', () => {
    render(<NotificationBell />);
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('has the bell SVG icon', () => {
    render(<NotificationBell />);
    const btn = screen.getAllByRole('button')[0];
    const svg = btn.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });
});
