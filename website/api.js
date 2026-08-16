const api = {
  base: "/api/v1",
  token: null as string | null,
  refreshToken: null as string | null,
  user: null as any,

  async request(path: string, options: any = {}) {
    const url = this.base + path;
    const headers: any = { "Content-Type": "application/json", "x-trace-id": crypto.randomUUID() };
    if (this.token) headers["Authorization"] = `Bearer ${this.token}`;

    const res = await fetch(url, { ...options, headers: { ...headers, ...options.headers } });

    if (res.status === 401 && this.refreshToken) {
      const refreshed = await fetch(this.base + "/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refreshToken: this.refreshToken }),
      });
      if (refreshed.ok) {
        const t = await refreshed.json();
        this.token = t.data.accessToken;
        this.refreshToken = t.data.refreshToken;
        localStorage.setItem("quantive_token", this.token);
        localStorage.setItem("quantive_refresh", this.refreshToken);
        headers["Authorization"] = `Bearer ${this.token}`;
        const retry = await fetch(url, { ...options, headers });
        return retry.json();
      }
      this.logout();
      return null;
    }
    return res.json();
  },

  async login(email: string, password: string) {
    const data = await this.request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (data.success) {
      this.token = data.data.accessToken;
      this.refreshToken = data.data.refreshToken;
      this.user = data.data.user;
      localStorage.setItem("quantive_token", this.token);
      localStorage.setItem("quantive_refresh", this.refreshToken);
      localStorage.setItem("quantive_user", JSON.stringify(this.user));
    }
    return data;
  },

  async register(data: any) {
    const res = await this.request("/auth/register", { method: "POST", body: JSON.stringify(data) });
    return res;
  },

  async logout() {
    if (this.token) await this.request("/auth/logout", { method: "POST" });
    this.token = null;
    this.refreshToken = null;
    this.user = null;
    localStorage.removeItem("quantive_token");
    localStorage.removeItem("quantive_refresh");
    localStorage.removeItem("quantive_user");
  },

  async fetchMe() {
    const data = await this.request("/auth/me");
    if (data.success) this.user = data.data;
    return data;
  },

  async get(path: string) { return this.request(path); },

  async post(path: string, body: any) {
    return this.request(path, { method: "POST", body: JSON.stringify(body) });
  },

  async patch(path: string, body: any) {
    return this.request(path, { method: "PATCH", body: JSON.stringify(body) });
  },

  async del(path: string) { return this.request(path, { method: "DELETE" }); },

  restore() {
    this.token = localStorage.getItem("quantive_token");
    this.refreshToken = localStorage.getItem("quantive_refresh");
    const u = localStorage.getItem("quantive_user");
    if (u) this.user = JSON.parse(u);
    return !!this.token;
  },
};
