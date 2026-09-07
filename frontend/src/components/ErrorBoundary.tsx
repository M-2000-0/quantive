import { Component, type ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
 children: ReactNode;
 fallback?: ReactNode;
 onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface State {
 hasError: boolean;
 error: Error | null;
 errorInfo: React.ErrorInfo | null;
}

export default class ErrorBoundary extends Component<Props, State> {
 constructor(props: Props) {
 super(props);
 this.state = { hasError: false, error: null, errorInfo: null };
 }

 static getDerivedStateFromError(error: Error): Partial<State> {
 return { hasError: true, error };
 }

 componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
 this.setState({ errorInfo });
 this.props.onError?.(error, errorInfo);

 // Log to console in development
 if (import.meta.env.DEV) {
 console.error('[ErrorBoundary]', error, errorInfo);
 }
 }

 handleReload = () => {
 this.setState({ hasError: false, error: null, errorInfo: null });
 window.location.reload();
 };

 handleReset = () => {
 this.setState({ hasError: false, error: null, errorInfo: null });
 };

 render() {
 if (this.state.hasError) {
 if (this.props.fallback) {
 return this.props.fallback;
 }

 return (
  <div className="min-h-[400px] flex items-center justify-center p-8">
  <div className="max-w-lg w-full bg-white dark:bg-gray-900 rounded-xl shadow-lg p-8 text-center">
  <div className="text-5xl mb-4"> <AlertTriangle className="w-4 h-4 inline" /> </div>
  <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2">Something went wrong</h2>
  <p className="text-gray-500 dark:text-gray-400 mb-6">
  An unexpected error occurred. This has been logged and our team has been notified.
  </p>

  <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 mb-6 text-left">
  <p className="text-sm font-mono text-red-600 dark:text-red-400 break-all">
  {this.state.error?.message || 'Unknown error'}
  </p>
  {this.state.errorInfo?.componentStack && (
  <details className="mt-2">
  <summary className="text-xs text-gray-400 dark:text-gray-500 cursor-pointer hover:text-gray-600 dark:hover:text-gray-300">
  Component stack
  </summary>
  <pre className="text-xs text-gray-500 dark:text-gray-400 mt-1 overflow-auto max-h-32 whitespace-pre-wrap">
  {this.state.errorInfo.componentStack}
  </pre>
  </details>
  )}
  </div>

  <div className="flex gap-3 justify-center">
  <button
  onClick={this.handleReset}
  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
  >
  Try Again
  </button>
  <button
  onClick={this.handleReload}
  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
  >
  Reload Page
  </button>
  </div>
  </div>
  </div>
 );
 }

 return this.props.children;
 }
}
