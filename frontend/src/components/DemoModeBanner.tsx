import { Link } from 'react-router-dom';
import { useDemoMode } from '../stores/demoMode';

export default function DemoModeBanner() {
  const { isDemoMode, disableDemoMode } = useDemoMode();
  if (!isDemoMode) return null;
  return (
    <div
      role="status"
      style={{
        background: '#fffbeb',
        borderBottom: '1px solid #fde68a',
        color: '#92400e',
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
        style={{ border: '1px solid #fcd34d', background: '#fff', borderRadius: 6, padding: '2px 10px', cursor: 'pointer' }}
      >
        Exit demo
      </button>
    </div>
  );
}
