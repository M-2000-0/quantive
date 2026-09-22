import { NavLink, Outlet, Link } from 'react-router-dom';

const ITEMS = [
  { label: 'Dashboard', to: '/personal' },
  { label: 'My Profile', to: '/personal/profile' },
  { label: 'Opportunities', to: '/personal/opportunities' },
  { label: 'Recommendations', to: '/personal/recommendations' },
  { label: 'Connections', to: '/personal/connections' },
  { label: 'Transactions', to: '/personal/transactions' },
  { label: 'Compliance', to: '/personal/compliance' },
  { label: 'Projection', to: '/personal/projection' },
  { label: 'Documents', to: '/personal/documents' },
  { label: 'Intelligence', to: '/personal/intelligence' },
  { label: 'Reports', to: '/personal/reports' },
  { label: 'Sovereign', to: '/personal/gov' },
  { label: 'Pricing', to: '/personal/pricing' },
  { label: 'Onboarding', to: '/personal/onboarding' },
];

export default function PersonalLayout() {
  return (
    <div className="qp-shell">
      <aside className="qp-side">
        <Link to="/personal" className="qp-brand">
          <span className="qp-mark">Q</span>
          <span>
            <strong>Quantive Personal</strong>
            <small>Tax intelligence</small>
          </span>
        </Link>
        <nav aria-label="Quantive Personal">
          {ITEMS.map((i) => (
            <NavLink
              key={i.to}
              to={i.to}
              end={i.to === '/personal'}
              className={({ isActive }) => `qp-nav${isActive ? ' active' : ''}`}
            >
              {i.label}
            </NavLink>
          ))}
        </nav>
        <div className="qp-sep" />
        <Link to="/dashboard" className="qp-ghost">
          ← Quantive workspace
        </Link>
        <p className="qp-note">Separate product. Separate data. Shared billing.</p>
      </aside>
      <main className="qp-main">
        <Outlet />
      </main>
    </div>
  );
}
