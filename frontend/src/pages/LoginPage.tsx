import { useState } from 'react';
import { useAuth } from '../stores/auth';
import { useNavigate, Link } from 'react-router-dom';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Authentication failed. Verify credentials and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden">
      {/* liquid glass backdrop */}
      <div className="absolute inset-0 -z-10 bg-[#eef2f7]" />
      <div className="absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-32 -left-32 w-[700px] h-[700px] rounded-full bg-gradient-to-br from-blue-400/25 via-violet-400/18 to-cyan-400/20 blur-[50px]" />
        <div className="absolute top-1/3 -right-40 w-[640px] h-[640px] rounded-full bg-gradient-to-br from-sky-400/18 via-indigo-400/18 to-blue-500/14 blur-[50px]" />
        <div className="absolute -bottom-40 left-1/4 w-[800px] h-[500px] rounded-full bg-gradient-to-br from-violet-400/12 via-fuchsia-400/10 to-blue-400/14 blur-[50px]" />
        <div className="absolute inset-0 bg-gradient-to-b from-white/30 via-transparent to-white/20" />
      </div>

      <div className="w-full max-w-md relative">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 shadow-xl shadow-blue-600/20 ring-1 ring-white/20 mb-5">
            <span className="text-white text-xl font-bold tracking-tight">Q</span>
          </div>
          <h1 className="text-2xl font-bold tracking-[0.12em] uppercase bg-gradient-to-br from-slate-900 to-slate-700 bg-clip-text text-transparent">Quantive</h1>
          <p className="text-sm font-medium tracking-wide text-slate-500 mt-1.5">Government Financial Optimization</p>
        </div>

        <div className="glass-strong rounded-[24px] p-8 relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-white/40 via-transparent to-white/10 pointer-events-none" />
          <div className="absolute top-0 left-6 right-6 h-px bg-gradient-to-r from-transparent via-white/70 to-transparent pointer-events-none" />
          <div className="relative">
            <h2 className="text-[17px] font-semibold tracking-tight text-slate-900 mb-1">Sign in to your account</h2>
            <p className="text-sm text-slate-500 mb-6">Enter your credentials to access the platform</p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-[12px] font-semibold uppercase tracking-widest text-slate-600 mb-1.5">
                  Email Address
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  className="w-full px-3.5 py-2.5 glass-input rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none transition-all"
                  placeholder="name@agency.gov"
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-[12px] font-semibold uppercase tracking-widest text-slate-600 mb-1.5">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  className="w-full px-3.5 py-2.5 glass-input rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none transition-all"
                  placeholder="Enter your password"
                />
              </div>

              {error && (
                <div className="rounded-xl px-3.5 py-2.5 text-sm text-red-700 bg-red-500/10 border border-red-500/20 backdrop-blur-md">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full glass-button-primary text-white text-sm font-semibold rounded-xl px-4 py-3 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {loading && (
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                )}
                {loading ? 'Authenticating...' : 'Sign In'}
              </button>
            </form>

            <div className="mt-6 pt-5 border-t border-white/40 text-center space-y-2">
              <p className="text-sm text-slate-500">
                <Link to="/register" className="font-semibold text-blue-600 hover:text-blue-700 transition-colors">
                  Request access
                </Link>
                <span className="mx-2 text-slate-300">·</span>
                <Link to="/forgot-password" className="font-medium text-slate-500 hover:text-slate-700 transition-colors">
                  Forgot password?
                </Link>
              </p>
            </div>
          </div>
        </div>

        <p className="text-center text-xs font-medium tracking-wide text-slate-500 mt-6 backdrop-blur-sm bg-white/40 border border-white/40 rounded-full px-4 py-2 w-fit mx-auto shadow-sm">
          Authorized personnel only. All access is logged and audited.
        </p>
      </div>
    </div>
  );
}
