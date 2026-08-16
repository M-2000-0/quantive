const BASE = import.meta.env.VITE_API_URL || "/api/v1";

let token: string | null = localStorage.getItem("q_token");
let refreshToken: string | null = localStorage.getItem("q_refresh");

export const api = {
  get token() { return token; },
  get isAuthenticated() { return !!token; },

  async request(path: string, opts: RequestInit = {}) {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(BASE + path, { ...opts, headers: { ...headers, ...(opts.headers as any) } });
    if (res.status === 401 && refreshToken) {
      const r = await fetch(BASE + "/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refreshToken }),
      });
      if (r.ok) {
        const t = await r.json();
        token = t.data.accessToken;
        refreshToken = t.data.refreshToken;
        localStorage.setItem("q_token", token!);
        localStorage.setItem("q_refresh", refreshToken!);
        headers["Authorization"] = `Bearer ${token}`;
        return fetch(BASE + path, { ...opts, headers }).then((r) => r.json());
      }
      api.logout();
      return null;
    }
    return res.json();
  },

  async login(email: string, password: string) {
    const data = await this.request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (data?.success) {
      token = data.data.accessToken;
      refreshToken = data.data.refreshToken;
      localStorage.setItem("q_token", token!);
      localStorage.setItem("q_refresh", refreshToken!);
      localStorage.setItem("q_user", JSON.stringify(data.data.user));
    }
    return data;
  },

  logout() {
    token = null;
    refreshToken = null;
    localStorage.removeItem("q_token");
    localStorage.removeItem("q_refresh");
    localStorage.removeItem("q_user");
    window.location.href = "/login";
  },

  get(path: string) { return this.request(path); },
  post(path: string, body?: any) { return this.request(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }); },
  patch(path: string, body?: any) { return this.request(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }); },
  del(path: string) { return this.request(path, { method: "DELETE" }); },
};
