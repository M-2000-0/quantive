import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useEffect, useState } from "react";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: "grid_view" },
  { to: "/transactions", label: "Transactions", icon: "swap_horiz" },
  { to: "/alerts", label: "Alerts", icon: "warning" },
  { to: "/cases", label: "Cases", icon: "folder_shared" },
  { to: "/automations", label: "Automations", icon: "bolt" },
  { to: "/blockchain", label: "Blockchain", icon: "link" },
  { to: "/settings", label: "Settings", icon: "settings" },
];

export function Layout() {
  const navigate = useNavigate();
  const [user, setUser] = useState<any>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    try { setUser(JSON.parse(localStorage.getItem("q_user") || "{}")); } catch {}
  }, []);

  async function handleLogout() {
    await api.post("/auth/logout").catch(() => {});
    api.logout();
  }

  return (
    <div className="flex h-screen overflow-hidden bg-surface">
      {/* Sidebar */}
      <aside className="hidden md:flex flex-col w-60 border-r border-surface-variant bg-surface shrink-0">
        <div className="p-5 border-b border-surface-variant/30">
          <h1 className="text-xl font-bold text-primary tracking-tight">Quantive</h1>
          <p className="text-[10px] text-on-variant/60 uppercase tracking-widest mt-0.5">Enterprise Compliance</p>
        </div>
        <nav className="flex-1 p-2 space-y-0.5">
          {NAV.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                  isActive ? "bg-primary/10 text-primary border-r-2 border-primary" : "text-on-variant hover:text-on-surface hover:bg-surface-high"
                }`
              }
            >
              <span className="material-symbols-outlined text-lg">{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-surface-variant/30">
          {user && (
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-surface-variant flex items-center justify-center text-xs font-semibold text-primary">
                {user.name?.charAt(0) || "U"}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-on-surface truncate">{user.name || "User"}</p>
                <p className="text-[10px] text-on-muted uppercase tracking-wider">{user.role || "Analyst"}</p>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-14 border-b border-surface-variant/30 bg-surface/80 backdrop-blur-md flex items-center justify-between px-4 shrink-0">
          <button className="md:hidden text-on-variant" onClick={() => setMenuOpen(!menuOpen)}>
            <span className="material-symbols-outlined">menu</span>
          </button>
          <div className="flex items-center gap-2 ml-auto">
            <button onClick={handleLogout} className="text-xs text-on-muted hover:text-on-variant transition-colors px-2 py-1 rounded hover:bg-surface-high">
              Logout
            </button>
          </div>
        </header>

        {/* Mobile menu */}
        {menuOpen && (
          <div className="md:hidden bg-surface-low border-b border-surface-variant p-2">
            {NAV.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setMenuOpen(false)}
                className={({ isActive }) =>
                  `block px-3 py-2 rounded-md text-sm ${isActive ? "text-primary bg-primary/10" : "text-on-variant"}`
                }
              >
                {label}
              </NavLink>
            ))}
          </div>
        )}

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
