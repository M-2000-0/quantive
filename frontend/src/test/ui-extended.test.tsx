import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ConfidenceBadge from '../components/ui/ConfidenceBadge';
import ProgressBar from '../components/ui/ProgressBar';

// ── ConfidenceBadge ─────────────────────────────────────────────────
describe('ConfidenceBadge', () => {
  it('renders score number', () => {
    render(<ConfidenceBadge score={85} />);
    expect(screen.getByText('85')).toBeInTheDocument();
  });

  it('shows High Confidence for score >= 75', () => {
    render(<ConfidenceBadge score={85} />);
    expect(screen.getByText('High Confidence')).toBeInTheDocument();
  });

  it('shows Medium Confidence for score 45-74', () => {
    render(<ConfidenceBadge score={60} />);
    expect(screen.getByText('Medium Confidence')).toBeInTheDocument();
  });

  it('shows Low Confidence for score < 45', () => {
    render(<ConfidenceBadge score={30} />);
    expect(screen.getByText('Low Confidence')).toBeInTheDocument();
  });

  it('hides label when showLabel=false', () => {
    const { container } = render(<ConfidenceBadge score={85} showLabel={false} />);
    expect(screen.queryByText('High Confidence')).toBeNull();
    // Score should still be visible
    expect(screen.getByText('85')).toBeInTheDocument();
  });

  it('clamps score to 0-100', () => {
    render(<ConfidenceBadge score={150} />);
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('handles score of 0', () => {
    render(<ConfidenceBadge score={0} />);
    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByText('Low Confidence')).toBeInTheDocument();
  });

  it('has SVG circle for progress', () => {
    const { container } = render(<ConfidenceBadge score={50} />);
    const circles = container.querySelectorAll('circle');
    expect(circles.length).toBe(2); // track + fill
  });
});

// ── ProgressBar ─────────────────────────────────────────────────────
describe('ProgressBar', () => {
  it('renders label when provided', () => {
    render(<ProgressBar value={0.5} label="Progress" />);
    expect(screen.getByText('Progress')).toBeInTheDocument();
  });

  it('renders percentage when showPercentage=true', () => {
    render(<ProgressBar value={0.75} showPercentage />);
    expect(screen.getByText('75%')).toBeInTheDocument();
  });

  it('clamps value to 0-100 range', () => {
    render(<ProgressBar value={1.5} showPercentage />);
    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('handles 0% value', () => {
    render(<ProgressBar value={0} showPercentage />);
    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  it('has liquid-progress class', () => {
    const { container } = render(<ProgressBar value={0.5} />);
    const progress = container.querySelector('.liquid-progress');
    expect(progress).toBeInTheDocument();
  });

  it('has liquid-progress-fill class', () => {
    const { container } = render(<ProgressBar value={0.5} />);
    const fill = container.querySelector('.liquid-progress-fill');
    expect(fill).toBeInTheDocument();
  });

  it('applies success variant styles', () => {
    const { container } = render(<ProgressBar value={0.5} variant="success" />);
    const fill = container.querySelector('.liquid-progress-fill');
    expect(fill?.className).toContain('emerald');
  });

  it('applies warning variant styles', () => {
    const { container } = render(<ProgressBar value={0.5} variant="warning" />);
    const fill = container.querySelector('.liquid-progress-fill');
    expect(fill?.className).toContain('amber');
  });

  it('applies danger variant styles', () => {
    const { container } = render(<ProgressBar value={0.5} variant="danger" />);
    const fill = container.querySelector('.liquid-progress-fill');
    expect(fill?.className).toContain('red');
  });

  it('sets width style based on value', () => {
    const { container } = render(<ProgressBar value={0.6} />);
    const fill = container.querySelector('.liquid-progress-fill');
    expect(fill).toHaveStyle({ width: '60%' });
  });

  it('has accessibility attributes', () => {
    render(<ProgressBar value={0.45} />);
    const fill = screen.getByRole('progressbar');
    expect(fill).toHaveAttribute('aria-valuenow', '45');
    expect(fill).toHaveAttribute('aria-valuemin', '0');
    expect(fill).toHaveAttribute('aria-valuemax', '100');
  });
});
