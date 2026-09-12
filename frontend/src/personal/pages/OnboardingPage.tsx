import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { personalApi, type PersonalOnboarding } from '../api';

export default function OnboardingPage() {
  const [data, setData] = useState<PersonalOnboarding | null>(null);
  const [sel, setSel] = useState<string[]>([]);
  const [single, setSingle] = useState('');
  const nav = useNavigate();

  const load = async () => setData(await personalApi.onboarding());
  useEffect(() => { load().catch(() => {}); }, []);

  const q = useMemo(() => {
    if (!data) return null;
    return data.questions[Math.min(data.current, data.questions.length - 1)] || null;
  }, [data]);

  useEffect(() => { setSel([]); setSingle(''); }, [q?.id]);

  if (!data || !q) return <p className="qp-muted">Preparing your profile — about 8 minutes, 24 questions max.</p>;

  const isMulti = q.kind === 'multi';
  const toggle = (o: string) =>
    setSel((s) => (s.includes(o) ? s.filter((x) => x !== o) : [...s, o]));

  const submit = async () => {
    const answer = isMulti ? sel : single;
    if ((isMulti && sel.length === 0) || (!isMulti && !single)) return;
    const next = await personalApi.answer(q.id, answer);
    setData(next);
    if (next.current >= next.questions.length) {
      await personalApi.completeOnboarding().catch(() => {});
      nav('/personal');
    }
  };

  const pct = Math.round((100 * data.current) / Math.max(1, data.total));

  return (
    <div>
      <h1>Let&apos;s build your financial profile.</h1>
      <p className="qp-muted">You don&apos;t need to know the tax rules. That&apos;s our job. ~8 minutes.</p>
      <p className="qp-muted">Question {Math.min(data.current + 1, data.total)} of {data.total} (baseline max {data.baseline_max}) — {pct}%</p>
      <div className="qp-card">
        <h3>{q.group}</h3>
        <h2>{q.prompt}</h2>
        <div className="qp-list">
          {q.options.map((o) => isMulti ? (
            <button key={o} className={`qp-opt${sel.includes(o) ? ' selected' : ''}`} onClick={() => toggle(o)}>{o}</button>
          ) : (
            <button key={o} className={`qp-opt${single === o ? ' selected' : ''}`} onClick={() => setSingle(o)}>{o}</button>
          ))}
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
          <button className="qp-btn" onClick={submit}>Continue</button>
          <button className="qp-btn secondary" onClick={async () => {
            const next = await personalApi.answer(q.id, isMulti ? ['skipped'] : 'skipped');
            setData(next);
          }}>Skip</button>
        </div>
      </div>
    </div>
  );
}
