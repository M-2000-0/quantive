import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ErrorBoundary from '../components/ErrorBoundary';
import { ToastProvider, useToast } from '../stores/toast';

// ─── ErrorBoundary ──────────────────────────────────────────────────────────

function ThrowingComponent({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error('Test error');
  return <div>All good</div>;
}

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={false} />
      </ErrorBoundary>
    );
    expect(screen.getByText('All good')).toBeInTheDocument();
  });

  it('renders fallback UI when child throws', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText('Test error')).toBeInTheDocument();
  });

  it('renders custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<div>Custom fallback</div>}>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText('Custom fallback')).toBeInTheDocument();
  });

  it('calls onError callback when error occurs', () => {
    const onError = vi.fn();
    render(
      <ErrorBoundary onError={onError}>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError.mock.calls[0][0].message).toBe('Test error');
  });

  it('Try Again button resets error state', () => {
    // Use a mutable flag so we can stop the throw after reset
    let shouldThrow = true;
    function ConditionalThrower() {
      if (shouldThrow) throw new Error('boom');
      return <div>Recovered</div>;
    }

    const { unmount } = render(
      <ErrorBoundary>
        <ConditionalThrower />
      </ErrorBoundary>
    );
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    // Stop the component from throwing
    shouldThrow = false;
    fireEvent.click(screen.getByText('Try Again'));

    expect(screen.getByText('Recovered')).toBeInTheDocument();
    unmount();
  });
});

// ─── ToastProvider integration ──────────────────────────────────────────────

function ToastConsumer() {
  const { addToast, toasts } = useToast();
  return (
    <div>
      <button onClick={() => addToast({ type: 'success', title: 'Saved', message: 'All changes saved' })}>
        Add Success
      </button>
      <button onClick={() => addToast({ type: 'error', title: 'Failed', message: 'Something broke' })}>
        Add Error
      </button>
      <button onClick={() => addToast({ type: 'info', title: 'FYI' })}>
        Add Info
      </button>
      <button onClick={() => addToast({ type: 'warning', title: 'Caution' })}>
        Add Warning
      </button>
      <span data-testid="count">{toasts.length}</span>
    </div>
  );
}

describe('ToastProvider', () => {
  it('renders children', () => {
    render(
      <ToastProvider>
        <div>Child content</div>
      </ToastProvider>
    );
    expect(screen.getByText('Child content')).toBeInTheDocument();
  });

  it('adds and displays success toasts', async () => {
    render(
      <ToastProvider>
        <ToastConsumer />
      </ToastProvider>
    );

    expect(screen.getByTestId('count').textContent).toBe('0');

    await act(async () => {
      fireEvent.click(screen.getByText('Add Success'));
    });

    expect(screen.getByText('Saved')).toBeInTheDocument();
    expect(screen.getByText('All changes saved')).toBeInTheDocument();
    expect(screen.getByTestId('count').textContent).toBe('1');
  });

  it('adds and displays error toasts', async () => {
    render(
      <ToastProvider>
        <ToastConsumer />
      </ToastProvider>
    );

    await act(async () => {
      fireEvent.click(screen.getByText('Add Error'));
    });

    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByText('Something broke')).toBeInTheDocument();
  });

  it('adds info toasts', async () => {
    render(
      <ToastProvider>
        <ToastConsumer />
      </ToastProvider>
    );

    await act(async () => {
      fireEvent.click(screen.getByText('Add Info'));
    });

    expect(screen.getByText('FYI')).toBeInTheDocument();
  });

  it('adds warning toasts', async () => {
    render(
      <ToastProvider>
        <ToastConsumer />
      </ToastProvider>
    );

    await act(async () => {
      fireEvent.click(screen.getByText('Add Warning'));
    });

    expect(screen.getByText('Caution')).toBeInTheDocument();
  });

  it('displays toasts in role=status container with aria-live', async () => {
    render(
      <ToastProvider>
        <ToastConsumer />
      </ToastProvider>
    );

    await act(async () => {
      fireEvent.click(screen.getByText('Add Success'));
    });

    const statusElements = screen.getAllByRole('status');
    expect(statusElements.length).toBeGreaterThan(0);
    expect(statusElements[0]).toHaveAttribute('aria-live', 'polite');
  });

  it('dismissing a toast removes it', async () => {
    render(
      <ToastProvider>
        <ToastConsumer />
      </ToastProvider>
    );

    await act(async () => {
      fireEvent.click(screen.getByText('Add Success'));
    });

    expect(screen.getByText('Saved')).toBeInTheDocument();

    await act(async () => {
      const dismissBtn = screen.getByLabelText('Dismiss notification');
      fireEvent.click(dismissBtn);
    });

    expect(screen.queryByText('Saved')).not.toBeInTheDocument();
  });
});

// ─── ToastProvider convenience methods ──────────────────────────────────────

function ConvenienceConsumer() {
  const { success, error, warning, info } = useToast();
  return (
    <div>
      <button onClick={() => success('Done', 'Operation complete')}>success()</button>
      <button onClick={() => error('Oops', 'It broke')}>error()</button>
      <button onClick={() => warning('Watch out')}>warning()</button>
      <button onClick={() => info('FYI', 'Just so you know')}>info()</button>
    </div>
  );
}

describe('ToastProvider convenience methods', () => {
  it('success() creates a success toast', async () => {
    render(
      <ToastProvider>
        <ConvenienceConsumer />
      </ToastProvider>
    );

    await act(async () => {
      fireEvent.click(screen.getByText('success()'));
    });

    expect(screen.getByText('Done')).toBeInTheDocument();
    expect(screen.getByText('Operation complete')).toBeInTheDocument();
  });

  it('error() creates an error toast', async () => {
    render(
      <ToastProvider>
        <ConvenienceConsumer />
      </ToastProvider>
    );

    await act(async () => {
      fireEvent.click(screen.getByText('error()'));
    });

    expect(screen.getByText('Oops')).toBeInTheDocument();
    expect(screen.getByText('It broke')).toBeInTheDocument();
  });

  it('warning() creates a warning toast', async () => {
    render(
      <ToastProvider>
        <ConvenienceConsumer />
      </ToastProvider>
    );

    await act(async () => {
      fireEvent.click(screen.getByText('warning()'));
    });

    expect(screen.getByText('Watch out')).toBeInTheDocument();
  });

  it('info() creates an info toast', async () => {
    render(
      <ToastProvider>
        <ConvenienceConsumer />
      </ToastProvider>
    );

    await act(async () => {
      fireEvent.click(screen.getByText('info()'));
    });

    expect(screen.getByText('FYI')).toBeInTheDocument();
    expect(screen.getByText('Just so you know')).toBeInTheDocument();
  });
});
