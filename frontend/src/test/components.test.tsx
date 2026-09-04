import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import Card, { CardHeader } from '../components/ui/Card';
import StatCard from '../components/ui/StatCard';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { ChartColumn as BarChart3 } from 'lucide-react';

// ── Card ────────────────────────────────────────────────────────────
describe('Card', () => {
  it('renders children', () => {
    render(<Card><p>Test content</p></Card>);
    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('applies padding by default', () => {
    const { container } = render(<Card><p>Content</p></Card>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('p-6');
  });

  it('removes padding when padding=false', () => {
    const { container } = render(<Card padding={false}><p>Content</p></Card>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).not.toContain('p-6');
  });

  it('applies custom className', () => {
    const { container } = render(<Card className="my-custom-class"><p>Content</p></Card>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('my-custom-class');
  });

  it('has glass-card class', () => {
    const { container } = render(<Card><p>Content</p></Card>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('glass-card');
  });
});

// ── CardHeader ──────────────────────────────────────────────────────
describe('CardHeader', () => {
  it('renders title', () => {
    render(<CardHeader title="My Title" />);
    expect(screen.getByText('My Title')).toBeInTheDocument();
  });

  it('renders subtitle when provided', () => {
    render(<CardHeader title="Title" subtitle="Subtitle text" />);
    expect(screen.getByText('Subtitle text')).toBeInTheDocument();
  });

  it('renders action when provided', () => {
    render(<CardHeader title="Title" action={<button>Action</button>} />);
    expect(screen.getByText('Action')).toBeInTheDocument();
  });

  it('does not render subtitle when not provided', () => {
    const { container } = render(<CardHeader title="Title" />);
    expect(container.querySelector('p')).toBeNull();
  });
});

// ── StatCard ────────────────────────────────────────────────────────
describe('StatCard', () => {
  it('renders label and value', () => {
    render(<StatCard label="Total Debt" value="$1.5M" />);
    expect(screen.getByText('Total Debt')).toBeInTheDocument();
    expect(screen.getByText('$1.5M')).toBeInTheDocument();
  });

  it('renders icon when provided', () => {
    render(<StatCard label="Test" value="100" icon={<BarChart3 className="w-5 h-5" />} />);
    expect(screen.getByText('BarChart3')).toBeInTheDocument();
  });

  it('renders change when provided', () => {
    render(<StatCard label="Test" value="100" change={5.2} />);
    expect(screen.getByText(/5\.2%/)).toBeInTheDocument();
  });

  it('renders changeLabel when provided', () => {
    render(<StatCard label="Test" value="100" changeLabel="vs last month" />);
    expect(screen.getByText('vs last month')).toBeInTheDocument();
  });

  it('has glass-card class', () => {
    const { container } = render(<StatCard label="Test" value="100" />);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('glass-card');
  });
});

// ── Badge ───────────────────────────────────────────────────────────
describe('Badge', () => {
  it('renders children text', () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('applies default variant styles', () => {
    const { container } = render(<Badge>Test</Badge>);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain('bg-white/60');
  });

  it('applies success variant styles', () => {
    const { container } = render(<Badge variant="success">OK</Badge>);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain('emerald');
  });

  it('applies danger variant styles', () => {
    const { container } = render(<Badge variant="danger">Error</Badge>);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain('red');
  });

  it('applies info variant styles', () => {
    const { container } = render(<Badge variant="info">Info</Badge>);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain('blue');
  });

  it('applies sm size by default', () => {
    const { container } = render(<Badge>Test</Badge>);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain('text-[11px]');
  });

  it('applies md size when specified', () => {
    const { container } = render(<Badge size="md">Test</Badge>);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain('text-xs');
  });
});

// ── Button ──────────────────────────────────────────────────────────
describe('Button', () => {
  it('renders children text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('renders as button element', () => {
    render(<Button>Test</Button>);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('applies primary variant by default', () => {
    render(<Button>Test</Button>);
    const btn = screen.getByRole('button');
    expect(btn.className).toContain('glass-button-primary');
  });

  it('applies secondary variant', () => {
    render(<Button variant="secondary">Test</Button>);
    const btn = screen.getByRole('button');
    expect(btn.className).toContain('glass-button-secondary');
  });

  it('applies danger variant', () => {
    render(<Button variant="danger">Delete</Button>);
    const btn = screen.getByRole('button');
    expect(btn.className).toContain('from-red-600');
  });

  it('applies ghost variant', () => {
    render(<Button variant="ghost">Ghost</Button>);
    const btn = screen.getByRole('button');
    expect(btn.className).toContain('backdrop-blur-md');
  });

  it('disables button when disabled prop is true', () => {
    render(<Button disabled>Disabled</Button>);
    const btn = screen.getByRole('button');
    expect(btn).toBeDisabled();
  });

  it('disables button when loading', () => {
    render(<Button loading>Loading</Button>);
    const btn = screen.getByRole('button');
    expect(btn).toBeDisabled();
  });

  it('applies fullWidth class', () => {
    render(<Button fullWidth>Full</Button>);
    const btn = screen.getByRole('button');
    expect(btn.className).toContain('w-full');
  });

  it('applies sm size', () => {
    render(<Button size="sm">Small</Button>);
    const btn = screen.getByRole('button');
    expect(btn.className).toContain('px-3');
  });

  it('applies lg size', () => {
    render(<Button size="lg">Large</Button>);
    const btn = screen.getByRole('button');
    expect(btn.className).toContain('px-5');
  });

  it('renders leftIcon', () => {
    render(<Button leftIcon={<span>→</span>}>With Icon</Button>);
    expect(screen.getByText('→')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<Button className="my-class">Test</Button>);
    const btn = screen.getByRole('button');
    expect(btn.className).toContain('my-class');
  });
});
