import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const isValid = newPassword.length >= 8 && /[a-zA-Z]/.test(newPassword) && /[0-9]/.test(newPassword);
  const passwordsMatch = newPassword === confirmPassword;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!isValid) {
      setError('Password must be at least 8 characters with at least one letter and one digit.');
      return;
    }
    if (!passwordsMatch) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: newPassword }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to reset password');
      }
      setSuccess(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-lg shadow-xl p-8 text-center">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-red-100 mb-4">
              <svg className="h-7 w-7 text-red-600" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-slate-900 mb-2">Invalid Reset Link</h2>
            <p className="text-sm text-slate-500 mb-6">
              This password reset link is invalid or missing a token. Please request a new one.
            </p>
            <Link
              to="/forgot-password"
              className="inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-700"
            >
              Request new reset link →
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-lg bg-blue-600 mb-5">
            <span className="text-white text-xl font-bold">Q</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-wider uppercase">Quantive</h1>
          <p className="text-sm text-slate-400 mt-1.5 tracking-wide">Government Financial Optimization</p>
        </div>

        <div className="bg-white rounded-lg shadow-xl p-8">
          {success ? (
            <div className="text-center py-4">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-emerald-100 mb-4">
                <svg className="h-7 w-7 text-emerald-600" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-slate-900 mb-2">Password reset successfully</h2>
              <p className="text-sm text-slate-500 mb-6">
                Your password has been updated. You can now sign in with your new password.
              </p>
              <Link
                to="/login"
                className="inline-flex items-center gap-2 bg-blue-600 text-white text-sm font-medium rounded-md px-5 py-2.5 hover:bg-blue-700 transition-colors"
              >
                Sign In →
              </Link>
            </div>
          ) : (
            <>
              <h2 className="text-lg font-semibold text-slate-900 mb-1">Set new password</h2>
              <p className="text-sm text-slate-500 mb-6">
                Enter your new password below. Must be at least 8 characters with letters and numbers.
              </p>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label htmlFor="newPassword" className="block text-sm font-medium text-slate-700 mb-1">
                    New Password
                  </label>
                  <input
                    id="newPassword"
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                    className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    placeholder="At least 8 characters"
                  />
                  {newPassword.length > 0 && (
                    <div className="mt-1.5 flex gap-1.5">
                      <div className={`h-1 flex-1 rounded-full ${newPassword.length >= 8 ? 'bg-emerald-500' : 'bg-slate-200'}`} />
                      <div className={`h-1 flex-1 rounded-full ${/[a-zA-Z]/.test(newPassword) ? 'bg-emerald-500' : 'bg-slate-200'}`} />
                      <div className={`h-1 flex-1 rounded-full ${/[0-9]/.test(newPassword) ? 'bg-emerald-500' : 'bg-slate-200'}`} />
                    </div>
                  )}
                </div>

                <div>
                  <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-700 mb-1">
                    Confirm Password
                  </label>
                  <input
                    id="confirmPassword"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                    className={`w-full px-3 py-2 border rounded-md text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors ${
                      confirmPassword.length > 0 && !passwordsMatch
                        ? 'border-red-300 focus:border-red-500'
                        : 'border-slate-300 focus:border-blue-500'
                    }`}
                    placeholder="Re-enter your password"
                  />
                  {confirmPassword.length > 0 && !passwordsMatch && (
                    <p className="mt-1 text-xs text-red-600">Passwords do not match</p>
                  )}
                </div>

                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-md px-3 py-2.5 text-sm text-red-700">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading || !isValid || !passwordsMatch}
                  className="w-full bg-blue-600 text-white text-sm font-medium rounded-md px-4 py-2.5 hover:bg-blue-700 active:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading && (
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  )}
                  {loading ? 'Resetting...' : 'Reset Password'}
                </button>
              </form>

              <div className="mt-6 pt-5 border-t border-white/40 text-center">
                <Link to="/login" className="text-sm text-slate-500 hover:text-slate-700 transition-colors">
                  ← Back to sign in
                </Link>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
