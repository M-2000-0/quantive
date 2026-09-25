import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, TrendingUp } from 'lucide-react';
import { api } from '../api';
import type { WhatIfScenarios, WhatIfScenarioRung } from '../types';

function formatCurrency(value: number): string {
  if (value >= 1e12) return `$${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

function fmtSigned(v: number): string {
  return `${v < 0 ? '−' : '+'}${formatCurrency(Math.abs(v))}`;
}

/**
 * What-if panel — the same deterministic rate-shock math the AI advisor
 * quotes (floating/short-dated repricing share, −D×Δy×P MTM), rendered as
 * two linked charts: annual interest cost and mark-to-market across the
 * 25/50/100/200bps ladder. Bars scale per chart; colors read direction.
 */
export default function WhatIfPanel() {
  const [data, setData] = useState<WhatIfScenarios | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<number>(0); // bps of the selected rung; 0 = base

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setData(await api.whatif.scenarios());
      const first = (data?.scenarios || []).find((r) => r.bps > 0);
      if (first) setActive(first.bps);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load scenarios');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) {
    return (
      <section className="panel" aria-label="What-if analysis" style={{ minHeight: 260 }}>
        <div className="panel-header"><h2>What-if analysis</h2></div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 48, color: '#6b7280' }}>
          <Loader2 size={22} style={{ animation: 'spin 1s linear infinite', marginRight: 8 }} />
          Loading scenarios…
        </div>
      </section>
    );
  }

  if (error || !data || data.scenarios.length === 0) {
    return (
      <section className="panel" aria-label="What-if analysis">
        <div className="panel-header"><h2>What-if analysis</h2></div>
        <p style={{ fontSize: 13, color: '#6b7280', padding: 16 }}>
          {error || data?.note || 'No scenario data available.'}
        </p>
      </section>
    );
  }

  const shocks = data.scenarios.filter((r) => r.bps > 0);
  const selected: WhatIfScenarioRung | undefined =
    data.scenarios.find((r) => r.bps === active) || data.scenarios[0];
  const maxInterest = Math.max(...data.scenarios.map((r) => r.annual_interest), 1);
  const maxAbsMtm = Math.max(...shocks.map((r) => Math.abs(r.mtm_impact)), 1);
  const exposures = Object.entries(data.currency_exposures || {});

  return (
    <section className="panel" aria-label="What-if analysis">
      <div className="panel-header">
        <h2>What-if analysis</h2>
        <span style={{ fontSize: 11, color: '#6b7280' }}>
          {data.base
            ? `${formatCurrency(data.base.total_principal)} · ${data.base.instrument_count} instruments · repricing share ~${data.base.repricing_share_pct.toFixed(0)}%`
            : ''}
        </span>
      </div>

      {/* Scenario selector */}
      <div role="tablist" aria-label="Rate shock scenarios" style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 14 }}>
        {data.scenarios.map((r) => (
          <button
            key={r.bps}
            type="button"
            role="tab"
            aria-selected={r.bps === active}
            onClick={() => setActive(r.bps)}
            style={{
              padding: '5px 12px', borderRadius: 999, fontSize: 12, cursor: 'pointer',
              border: r.bps === active ? '1px solid #2563eb' : '1px solid #e5e7eb',
              background: r.bps === active ? '#eff6ff' : '#fff',
              color: r.bps === active ? '#1d4ed8' : '#374151', fontWeight: r.bps === active ? 600 : 400,
            }}
          >
            {r.label}
          </button>
        ))}
      </div>

      {selected && (
        <p style={{ fontSize: 13, color: '#111827', margin: '0 0 14px' }}>
          {selected.bps === 0 ? (
            <>Today: <strong>{formatCurrency(selected.annual_interest)}</strong> annual interest on the live book.</>
          ) : (
            <>
              If rates rise <strong>{selected.bps.toFixed(0)}bps</strong>: annual interest
              goes <strong>{formatCurrency(data.scenarios[0].annual_interest)} → {formatCurrency(selected.annual_interest)}</strong>
              {' '}({fmtSigned(selected.interest_delta)}/yr) and the locked book marks
              to <strong style={{ color: selected.mtm_impact < 0 ? '#dc2626' : '#16a34a' }}>{fmtSigned(selected.mtm_impact)}</strong>.
            </>
          )}
        </p>
      )}

      {/* Chart 1: annual interest cost per scenario */}
      <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', color: '#6b7280', marginBottom: 6 }}>
        ANNUAL INTEREST COST
      </div>
      <div className="chart" role="list" aria-label="Annual interest cost by scenario. Select a scenario for exact values.">
        {data.scenarios.map((r) => (
          <button
            key={r.bps}
            type="button"
            role="listitem"
            className="bar-wrap"
            onClick={() => setActive(r.bps)}
            aria-label={`${r.label}: ${formatCurrency(r.annual_interest)} annual interest`}
            style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer' }}
          >
            <span
              className="bar"
              aria-hidden="true"
              style={{
                height: `${Math.max(4, (r.annual_interest / maxInterest) * 100)}%`,
                background: r.bps === active ? '#2563eb' : '#93c5fd',
              }}
            />
            <span className="bar-year" aria-hidden="true">
              {r.bps === 0 ? 'Base' : `+${r.bps.toFixed(0)}`}
            </span>
          </button>
        ))}
      </div>

      {/* Chart 2: mark-to-market impact per scenario */}
      <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', color: '#6b7280', margin: '18px 0 6px' }}>
        MARK-TO-MARKET IMPACT (FIRST-ORDER)
      </div>
      <div className="chart" role="list" aria-label="Mark-to-market impact by scenario. Select a scenario for exact values.">
        {shocks.map((r) => (
          <button
            key={r.bps}
            type="button"
            role="listitem"
            className="bar-wrap"
            onClick={() => setActive(r.bps)}
            aria-label={`${r.label}: mark-to-market ${fmtSigned(r.mtm_impact)}`}
            style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer' }}
          >
            <span
              className="bar"
              aria-hidden="true"
              style={{
                height: `${Math.max(4, (Math.abs(r.mtm_impact) / maxAbsMtm) * 100)}%`,
                background: r.bps === active ? '#dc2626' : '#fca5a5',
              }}
            />
            <span className="bar-year" aria-hidden="true">{`+${r.bps.toFixed(0)}`}</span>
          </button>
        ))}
      </div>

      {/* Currency exposures (FX what-ifs compose onto this) */}
      {exposures.length > 0 && (
        <div style={{ marginTop: 16, fontSize: 12, color: '#374151' }}>
          <TrendingUp size={13} style={{ verticalAlign: '-2px', marginRight: 4, color: '#6b7280' }} />
          Face-value exposure:{' '}
          {exposures.map(([ccy, v], i) => (
            <span key={ccy}>
              {i > 0 && ' · '}
              <strong>{ccy}</strong> {formatCurrency(v)}
            </span>
          ))}
        </div>
      )}

      <p style={{ fontSize: 11, color: '#9ca3af', margin: '12px 0 0' }}>
        {data.note} Ask the <Link to="/dashboard">Quantive AI</Link> assistant
        (bottom right) for any other shock — it answers from the same numbers.
      </p>
    </section>
  );
}
