import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock auth store
vi.mock('../stores/auth', () => ({
  useAuth: () => ({
    user: { email: 'test@company.com', role: 'admin' },
    token: 'test-token',
    isAuthenticated: true,
  }),
}));

import CommentThread from '../components/CommentThread';
import AnnotationLayer from '../components/AnnotationLayer';
import ComparisonView from '../components/ComparisonView';
import DataQualityIndicator from '../components/DataQualityIndicator';
import FilterBar from '../components/FilterBar';
import Timeline from '../components/Timeline';
import StatusTimeline from '../components/StatusTimeline';
import GoalTracker from '../components/GoalTracker';
import KeyboardShortcutHelp from '../components/KeyboardShortcutHelp';

// ─── CommentThread ────────────────────────────────────

describe('CommentThread', () => {
  it('renders existing comments', () => {
    render(<CommentThread resourceId="123" resourceType="portfolio" />);
    expect(screen.getByText(/Sarah Chen/)).toBeTruthy();
    expect(screen.getByText(/refinancing risk/)).toBeTruthy();
  });

  it('shows comment input', () => {
    render(<CommentThread resourceId="123" resourceType="portfolio" />);
    expect(screen.getByPlaceholderText(/comment/i)).toBeTruthy();
  });

  it('can type and submit a comment', () => {
    render(<CommentThread resourceId="123" resourceType="portfolio" />);
    const input = screen.getByPlaceholderText(/comment/i);
    fireEvent.change(input, { target: { value: 'Great analysis!' } });
    const postBtn = screen.getByRole('button', { name: /post/i });
    fireEvent.click(postBtn);
    expect(screen.getByText('Great analysis!')).toBeTruthy();
  });

  it('renders comment count', () => {
    render(<CommentThread resourceId="123" resourceType="portfolio" />);
    expect(screen.getByText(/Comments/)).toBeTruthy();
  });
});

// ─── AnnotationLayer ──────────────────────────────────

describe('AnnotationLayer', () => {
  it('renders annotations heading', () => {
    render(<AnnotationLayer resourceId="123" resourceType="portfolio" />);
    expect(screen.getByText('Annotations')).toBeTruthy();
  });

  it('can toggle annotation mode', () => {
    render(<AnnotationLayer resourceId="123" resourceType="portfolio" />);
    const addBtn = screen.getByText(/Add Note/i);
    fireEvent.click(addBtn);
    expect(screen.getByText(/Cancel/i)).toBeTruthy();
  });

  it('can cancel annotation mode', () => {
    render(<AnnotationLayer resourceId="123" resourceType="portfolio" />);
    const addBtn = screen.getByText(/Add Note/i);
    fireEvent.click(addBtn);
    const cancelBtn = screen.getByText(/Cancel/i);
    fireEvent.click(cancelBtn);
    expect(screen.getByText(/Add Note/i)).toBeTruthy();
  });
});

// ─── ComparisonView ───────────────────────────────────

describe('ComparisonView', () => {
  const items = [
    { id: '1', name: 'Strategy A', metrics: { return: { value: 0.052, unit: '%', format: 'percent' as const }, risk: { value: 3.1, unit: 'pts' } } },
    { id: '2', name: 'Strategy B', metrics: { return: { value: 0.048, unit: '%', format: 'percent' as const }, risk: { value: 2.5, unit: 'pts' } } },
  ];

  it('renders comparison items', () => {
    render(<ComparisonView items={items} metrics={[{ key: 'return', label: 'Return' }, { key: 'risk', label: 'Risk' }]} />);
    expect(screen.getByText('Strategy A')).toBeTruthy();
    expect(screen.getByText('Strategy B')).toBeTruthy();
  });

  it('shows metric values', () => {
    render(<ComparisonView items={items} metrics={[{ key: 'return', label: 'Return' }, { key: 'risk', label: 'Risk' }]} />);
    expect(screen.getByText('5.20%')).toBeTruthy();
    expect(screen.getByText('4.80%')).toBeTruthy();
  });

  it('renders with title', () => {
    render(<ComparisonView items={items} metrics={[{ key: 'return', label: 'Return' }]} title="Strategy Comparison" />);
    expect(screen.getByText('Strategy Comparison')).toBeTruthy();
  });

  it('renders metric labels', () => {
    render(<ComparisonView items={items} metrics={[{ key: 'return', label: 'Return' }, { key: 'risk', label: 'Risk Score' }]} />);
    expect(screen.getByText('Return')).toBeTruthy();
    expect(screen.getByText('Risk Score')).toBeTruthy();
  });
});

// ─── DataQualityIndicator ─────────────────────────────

describe('DataQualityIndicator', () => {
  const scores = [
    { category: 'Completeness', score: 95, details: 'Most fields present' },
    { category: 'Accuracy', score: 88, details: 'Minor issues' },
  ];

  it('renders with scores', () => {
    render(<DataQualityIndicator scores={scores} />);
    expect(screen.getByText('Data Quality')).toBeTruthy();
    expect(screen.getByText('Completeness')).toBeTruthy();
    expect(screen.getByText('Accuracy')).toBeTruthy();
  });

  it('shows overall score', () => {
    const { container } = render(<DataQualityIndicator scores={scores} />);
    // Score uses .toFixed(0) so 91.5 rounds to 92
    const svgTexts = container.querySelectorAll('text');
    const texts = Array.from(svgTexts).map(t => t.textContent);
    expect(texts.some(t => t?.includes('92'))).toBeTruthy();
  });

  it('renders with overall score override', () => {
    const { container } = render(<DataQualityIndicator scores={scores} overallScore={72} />);
    const svgTexts = container.querySelectorAll('text');
    const texts = Array.from(svgTexts).map(t => t.textContent);
    expect(texts.some(t => t?.includes('72'))).toBeTruthy();
  });

  it('shows freshness indicator', () => {
    render(<DataQualityIndicator scores={scores} dataFreshness="live" />);
    expect(screen.getByText('Live')).toBeTruthy();
  });
});

// ─── FilterBar ────────────────────────────────────────

describe('FilterBar', () => {
  const filters = [
    { key: 'currency', label: 'Currency', type: 'select' as const, options: [{ label: 'USD', value: 'USD' }, { label: 'EUR', value: 'EUR' }] },
    { key: 'search', label: 'Search', type: 'text' as const, placeholder: 'Search instruments...' },
  ];

  it('renders filter toggle', () => {
    render(<FilterBar filters={filters} values={{}} onChange={() => {}} />);
    expect(screen.getByText('Filters')).toBeTruthy();
  });

  it('expands to show filters', () => {
    render(<FilterBar filters={filters} values={{}} onChange={() => {}} />);
    fireEvent.click(screen.getByText('Filters'));
    expect(screen.getByText('Currency')).toBeTruthy();
    expect(screen.getByText('Search')).toBeTruthy();
  });

  it('shows active count badge', () => {
    render(<FilterBar filters={filters} values={{ currency: 'USD' }} onChange={() => {}} />);
    expect(screen.getByText('1')).toBeTruthy();
  });

  it('calls onReset when clear all clicked', () => {
    const onReset = vi.fn();
    render(<FilterBar filters={filters} values={{ currency: 'USD' }} onChange={() => {}} onReset={onReset} />);
    fireEvent.click(screen.getByText('Clear all'));
    expect(onReset).toHaveBeenCalled();
  });
});

// ─── Timeline ─────────────────────────────────────────

describe('Timeline', () => {
  const events = [
    { id: '1', title: 'Portfolio created', timestamp: '2025-01-15 10:00', type: 'create' as const, actor: 'Sarah' },
    { id: '2', title: 'Optimization run', timestamp: '2025-01-16 14:30', type: 'optimize' as const, actor: 'James' },
    { id: '3', title: 'Report generated', timestamp: '2025-01-17 09:15', type: 'export' as const, actor: 'System' },
  ];

  it('renders timeline events', () => {
    render(<Timeline events={events} />);
    expect(screen.getByText('Portfolio created')).toBeTruthy();
    expect(screen.getByText('Optimization run')).toBeTruthy();
    expect(screen.getByText('Report generated')).toBeTruthy();
  });

  it('renders actors', () => {
    render(<Timeline events={events} />);
    expect(screen.getByText(/Sarah/)).toBeTruthy();
    expect(screen.getByText(/James/)).toBeTruthy();
  });

  it('renders timestamps', () => {
    render(<Timeline events={events} />);
    expect(screen.getByText('2025-01-15 10:00')).toBeTruthy();
  });

  it('renders with custom title', () => {
    render(<Timeline events={events} title="Recent Activity" />);
    expect(screen.getByText('Recent Activity')).toBeTruthy();
  });
});

// ─── StatusTimeline ───────────────────────────────────

describe('StatusTimeline', () => {
  const steps = [
    { id: '1', label: 'Uploaded', status: 'completed' as const },
    { id: '2', label: 'Validated', status: 'completed' as const },
    { id: '3', label: 'Optimizing', status: 'active' as const },
    { id: '4', label: 'Complete', status: 'pending' as const },
  ];

  it('renders all steps', () => {
    render(<StatusTimeline steps={steps} />);
    expect(screen.getByText('Uploaded')).toBeTruthy();
    expect(screen.getByText('Validated')).toBeTruthy();
    expect(screen.getByText('Optimizing')).toBeTruthy();
    expect(screen.getByText('Complete')).toBeTruthy();
  });

  it('renders with title', () => {
    render(<StatusTimeline steps={steps} title="Optimization Progress" />);
    expect(screen.getByText('Optimization Progress')).toBeTruthy();
  });

  it('renders with timestamps', () => {
    const stepsWithTime = [
      { id: '1', label: 'Step 1', status: 'completed' as const, timestamp: '10:00 AM' },
      { id: '2', label: 'Step 2', status: 'active' as const, timestamp: '10:05 AM' },
    ];
    render(<StatusTimeline steps={stepsWithTime} />);
    expect(screen.getByText('10:00 AM')).toBeTruthy();
    expect(screen.getByText('10:05 AM')).toBeTruthy();
  });
});

// ─── GoalTracker ──────────────────────────────────────

describe('GoalTracker', () => {
  it('renders default goals', () => {
    render(<GoalTracker />);
    expect(screen.getByText('Portfolio Goals')).toBeTruthy();
    expect(screen.getByText(/Reduce Weighted Coupon/)).toBeTruthy();
    expect(screen.getByText(/Increase Green Bond Ratio/)).toBeTruthy();
  });

  it('renders goal values', () => {
    render(<GoalTracker />);
    expect(screen.getByText(/3\.82/)).toBeTruthy();
    expect(screen.getByText(/3\.5%/)).toBeTruthy();
  });

  it('shows goal progress bars', () => {
    const { container } = render(<GoalTracker />);
    const progressBars = container.querySelectorAll('[style*="width"]');
    expect(progressBars.length).toBeGreaterThan(0);
  });
});

// ─── KeyboardShortcutHelp ─────────────────────────────

describe('KeyboardShortcutHelp', () => {
  it('renders when open', () => {
    render(<KeyboardShortcutHelp isOpen={true} onClose={() => {}} />);
    expect(screen.getByText('Keyboard Shortcuts')).toBeTruthy();
  });

  it('renders shortcut categories', () => {
    render(<KeyboardShortcutHelp isOpen={true} onClose={() => {}} />);
    expect(screen.getByText('Navigation')).toBeTruthy();
    expect(screen.getByText('Actions')).toBeTruthy();
    expect(screen.getByText('Table')).toBeTruthy();
    expect(screen.getByText('General')).toBeTruthy();
  });

  it('renders shortcut descriptions', () => {
    render(<KeyboardShortcutHelp isOpen={true} onClose={() => {}} />);
    expect(screen.getByText('Open command palette')).toBeTruthy();
    expect(screen.getByText('New portfolio')).toBeTruthy();
  });

  it('renders nothing when closed', () => {
    const { container } = render(<KeyboardShortcutHelp isOpen={false} onClose={() => {}} />);
    expect(container.innerHTML).toBe('');
  });

  it('calls onClose when X button clicked', () => {
    const onClose = vi.fn();
    render(<KeyboardShortcutHelp isOpen={true} onClose={onClose} />);
    const closeBtn = screen.getByText('✕');
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalled();
  });
});
