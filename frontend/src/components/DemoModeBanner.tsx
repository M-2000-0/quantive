import { Link } from 'react-router-dom';
import { useDemoMode } from '../stores/demoMode';

export default function DemoModeBanner() {
  const { isDemoMode, disableDemoMode } = useDemoMode();
  if (!isDemoMode) return null;
  return (
    <div
      role="status"
      style={{
        background: '#eff6ff',
        borderBottom: '1px solid #bfdbfe',
        color: '#1e40af',
        fontSize: 13,
        padding: '8px 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 12,
      }}
    >
      <span>
        Demo mode is on — showing sample data. <Link to="/dashboard">Open dashboard</Link>
      </span>
      <button
        type="button"
        onClick={disableDemoMode}
        style={{ border: '1px solid #93c5fd', background: '#fff', borderRadius: 6, padding: '2px 10px', cursor: 'pointer' }}
      >
        Exit demo
      </button>
    </div>
  );
}
