import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import PerformanceMonitor from '../components/PerformanceMonitor';

describe('PerformanceMonitor', () => {
  it('renders summary stats', () => {
    render(<PerformanceMonitor />);
    expect(screen.getAllByText('Web Vitals').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('API Error Rate').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Uptime').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Active Connections').length).toBeGreaterThanOrEqual(1);
  });

  it('shows vitals tab by default', () => {
    render(<PerformanceMonitor />);
    expect(screen.getByText('LCP')).toBeDefined();
    expect(screen.getByText('FID')).toBeDefined();
    expect(screen.getByText('CLS')).toBeDefined();
    expect(screen.getByText('TTFB')).toBeDefined();
    expect(screen.getByText('INP')).toBeDefined();
    expect(screen.getByText('FCP')).toBeDefined();
  });

  it('switches to API Performance tab', async () => {
    render(<PerformanceMonitor />);
    fireEvent.click(screen.getByText('API Performance'));
    await waitFor(() => {
      expect(screen.getByText('POST /auth/login')).toBeDefined();
      expect(screen.getByText('GET /portfolios')).toBeDefined();
      expect(screen.getByText('GET /market/data')).toBeDefined();
    });
  });

  it('switches to System Health tab', async () => {
    render(<PerformanceMonitor />);
    fireEvent.click(screen.getByText('System Health'));
    await waitFor(() => {
      expect(screen.getByText('Resource Usage')).toBeDefined();
      expect(screen.getByText('System Info')).toBeDefined();
      expect(screen.getByText('CPU')).toBeDefined();
      expect(screen.getByText('Memory')).toBeDefined();
    });
  });

  it('shows system info metrics', async () => {
    render(<PerformanceMonitor />);
    fireEvent.click(screen.getByText('System Health'));
    await waitFor(() => {
      expect(screen.getByText('Bundle Size (gzip)')).toBeDefined();
      expect(screen.getByText('187KB')).toBeDefined();
      expect(screen.getByText('885 passing')).toBeDefined();
    });
  });

  it('shows API endpoint health status', async () => {
    render(<PerformanceMonitor />);
    fireEvent.click(screen.getByText('API Performance'));
    await waitFor(() => {
      expect(screen.getAllByText(/Healthy|Slow|Critical/).length).toBeGreaterThan(0);
    });
  });
});
