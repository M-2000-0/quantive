import { useEffect, useState } from 'react';
import { personalApi } from '../api';

export default function ProfilePage() {
  const [groups, setGroups] = useState<Record<string, any[]>>({});
  const load = async () => setGroups((await personalApi.profile()).groups || {});
  useEffect(() => { load().catch(() => {}); }, []);

  return (
    <div>
      <h1>Your Financial Profile</h1>
      <p className="qp-muted">What Quantive believes it knows. You control it — confirm, edit, remove.</p>
      {Object.entries(groups).map(([cat, facts]) => (
        <section key={cat} className="qp-card" style={{ marginTop: 12 }}>
          <h3>{cat}</h3>
          {facts.map((f: any) => (
            <div key={f.id} className="qp-row" style={{ marginTop: 8 }}>
              <h4>{f.key}</h4>
              <p>{f.value || JSON.stringify(f.value_json?.values || [])} · {f.status} · {f.source}</p>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="qp-btn secondary" onClick={async () => {
                  await personalApi.upsertFact({ category: cat, key: f.key, value: f.value, value_json: f.value_json, status: 'confirmed', confidence: 'user_confirmed' });
                  load();
                }}>Confirm</button>
                <button className="qp-btn secondary" onClick={async () => {
                  const v = prompt('Correct value:', f.value || '');
                  if (v !== null) {
                    await personalApi.upsertFact({ category: cat, key: f.key, value: v, status: 'confirmed', confidence: 'user_confirmed' });
                    load();
                  }
                }}>Edit</button>
                <button className="qp-btn secondary" onClick={async () => {
                  await personalApi.deleteFact(f.id); load();
                }}>Remove</button>
              </div>
            </div>
          ))}
        </section>
      ))}
      {Object.keys(groups).length === 0 && <p className="qp-muted">No facts yet — start onboarding.</p>}
    </div>
  );
}
