import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  if (api.isAuthenticated) {
    navigate("/dashboard", { replace: true });
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result = await api.login(email, password);
      if (result?.success) {
        navigate("/dashboard", { replace: true });
      } else {
        setError(result?.error || "Invalid credentials");
      }
    } catch {
      setError("Connection error. Ensure the API is running.");
    }
    setLoading(false);
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="w-3 h-3 bg-primary rounded-full mx-auto mb-3"></div>
          <h1 className="text-2xl font-bold text-on-surface">Quantive</h1>
          <p className="text-sm text-on-muted mt-1">Enterprise Compliance</p>
        </div>
        <form onSubmit={handleSubmit} className="bg-surface-container border border-surface-variant rounded-lg p-6 space-y-4">
          <div>
            <label className="block text-xs text-on-muted uppercase tracking-wider mb-1.5">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-surface-low border border-surface-variant rounded px-3 py-2 text-sm text-on-surface placeholder:text-on-muted/40 focus:outline-none focus:border-primary"
              placeholder="you@company.io"
              required
            />
          </div>
          <div>
            <label className="block text-xs text-on-muted uppercase tracking-wider mb-1.5">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-surface-low border border-surface-variant rounded px-3 py-2 text-sm text-on-surface placeholder:text-on-muted/40 focus:outline-none focus:border-primary"
              placeholder="&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;"
              required
            />
          </div>
          {error && <p className="text-xs text-error">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary text-black font-semibold py-2.5 rounded text-sm hover:brightness-110 transition-all disabled:opacity-60"
          >
            {loading ? "Authenticating..." : "Access Terminal"}
          </button>
        </form>
        <p className="text-center text-xs text-on-muted mt-4">
          &copy; 2026 Quantive. All rights reserved.
        </p>
      </div>
    </div>
  );
}
