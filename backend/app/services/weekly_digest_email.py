"""Weekly Digest Email — track record, top discovery signals, bubble flags.

Collects the week's intelligence from live services, renders a single branded
HTML email, and sends it to users who opted in via their notification
settings (`weekly_digest: true`).

Sections:
  1. Track Record     — wins/losses/hit rate + score calibration trend
  2. Top Discovery    — highest-scoring signals recorded this week
  3. Bubble Flags     — high/extreme bubble-risk assets
  4. Market Context   — volatility regime + asset counts from the daily digest

Sending uses the existing email provider stack (SendGrid/Resend/log-only).
The send is idempotent per ISO week: a `weekly_digest_last_sent` marker
prevents duplicate sends.
"""
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("quantive.weekly_digest")

_last_send_marker: dict[str, str] = {}  # user_id -> ISO week key


def _week_key(now: datetime | None = None) -> str:
    """ISO week identifier like 2026-W36."""
    now = now or datetime.now(timezone.utc)
    year, week, _ = now.isocalendar()
    return f"{year}-W{week:02d}"


# ── Data Collection ─────────────────────────────────────────────────

def _collect_track_record() -> dict:
    try:
        from app.services.signal_outcome_tracker import get_track_record, get_calibration
        record = get_track_record()
        cal = get_calibration()
        return {
            "has_data": record.get("has_data", False),
            "wins": record.get("wins", 0),
            "losses": record.get("losses", 0),
            "flat": record.get("flat", 0),
            "hit_rate": record.get("hit_rate"),
            "total": record.get("total_signals", 0),
            "calibration_trend": cal.get("trend"),
            "best_bucket": None,
            "recent": (record.get("recent") or [])[:5],
        }
    except Exception as e:
        logger.warning("track record collection failed: %s", e)
        return {"has_data": False}


def _collect_discovery_signals(limit: int = 8) -> list[dict]:
    """Highest-scoring signals recorded in the last 7 days."""
    try:
        from datetime import datetime as _dt

        from app.models.signal_outcome import SignalOutcome
        from app.database import SessionLocal

        week_ago = (_dt.now(timezone.utc) - timedelta(days=7)).isoformat()
        db = SessionLocal()
        try:
            rows = (
                db.query(SignalOutcome)
                .filter(SignalOutcome.recorded_at >= week_ago)
                .order_by(SignalOutcome.strength.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "symbol": r.symbol,
                    "type": r.signal_type.replace("_", " ").title(),
                    "strength": r.strength,
                    "direction": r.direction,
                    "claim": (r.claim or "")[:110],
                }
                for r in rows
            ]
        finally:
            db.close()
    except Exception as e:
        logger.warning("discovery signal collection failed: %s", e)
        return []


def _collect_bubble_flags(limit: int = 6) -> list[dict]:
    """Current high/extreme bubble-risk assets."""
    try:
        from app.services.bubble_detector import scan_portfolio_for_bubbles
        from app.api.market_monitor_api import _asset_store
        from app.api.global_market_api import _global_asset_store

        assets = list(_asset_store.values()) + list(_global_asset_store.values())
        if not assets:
            return []

        scan = scan_portfolio_for_bubbles(assets)
        results = scan.get("scan_results") or []
        flagged = [
            {
                "symbol": (r.get("symbol") or "").split(":")[-1],
                "score": r.get("bubble_score"),
                "level": r.get("risk_level"),
                "patterns": [
                    (p.get("name") if isinstance(p, dict) else str(p))
                    for p in (r.get("pattern_details") or [])[:2]
                ],
            }
            for r in results
            if (r.get("risk_level") or "").upper() in ("HIGH", "EXTREME")
            and (r.get("bubble_score") or 0) >= 50
        ][:limit]
        return flagged
    except Exception as e:
        logger.warning("bubble flag collection failed: %s", e)
        return []


def _collect_market_context() -> dict:
    try:
        from app.services.daily_digest import generate_digest
        d = generate_digest()
        return {
            "headline": d.get("headline"),
            "volatility": (d.get("volatility") or {}).get("regime"),
            "total_tracked": (d.get("pulse") or {}).get("total_tracked", 0),
        }
    except Exception as e:
        logger.warning("market context collection failed: %s", e)
        return {}


def _collect_sentiment_shifts(limit: int = 6) -> dict:
    """Tickers whose news sentiment changed most this week vs last week.

    Compares mean sentiment of articles from the trailing 7 days against the
    prior 7 days. Returns biggest improvers and decliners.
    """
    try:
        from datetime import datetime as _dt, timedelta as _td

        from app.database import SessionLocal
        from app.models.news import NewsArticle
        from app.services.sentiment_analyzer import aggregate_sentiment
        from sqlalchemy import desc as desc_pub

        now = _dt.now(timezone.utc)
        this_start = (now - _td(days=7)).isoformat()
        prev_start = (now - _td(days=14)).isoformat()

        db = SessionLocal()
        try:
            rows = (
                db.query(
                    NewsArticle.tickers_json,
                    NewsArticle.sentiment_score,
                    NewsArticle.published_at,
                )
                .filter(NewsArticle.sentiment_score.isnot(None))
                .filter(NewsArticle.published_at >= prev_start)
                .order_by(desc_pub(NewsArticle.published_at))
                .limit(3000)
                .all()
            )
        finally:
            db.close()

        this_week: dict[str, list[float]] = {}
        prev_week: dict[str, list[float]] = {}
        for tickers, score, published in rows:
            if not tickers or score is None:
                continue
            pub = str(published or "")
            in_this = pub >= this_start
            for t in tickers[:3]:
                t = (t or "").upper()
                if not t or len(t) > 6:
                    continue
                if in_this:
                    this_week.setdefault(t, []).append(float(score))
                else:
                    prev_week.setdefault(t, []).append(float(score))

        shifts = []
        for t, scores in this_week.items():
            if len(scores) < 2:
                continue
            now_agg = aggregate_sentiment(scores)
            prev_agg = aggregate_sentiment(prev_week.get(t, []))
            if now_agg["mean"] is None:
                continue
            prev_mean = prev_agg.get("mean") if prev_agg.get("count", 0) >= 2 else None
            delta = (
                round(now_agg["mean"] - prev_mean, 3)
                if prev_mean is not None
                else None
            )
            shifts.append({
                "symbol": t,
                "this_mean": now_agg["mean"],
                "this_label": now_agg["label"],
                "this_count": now_agg["count"],
                "prev_mean": prev_mean,
                "delta": delta,
            })

        # Most significant absolute shifts first; new coverage counts as a shift
        shifts.sort(key=lambda s: abs(s["delta"] if s["delta"] is not None else 0.5), reverse=True)
        improvers = [s for s in shifts if (s["delta"] or 0) > 0.1][:limit]
        decliners = [s for s in shifts if (s["delta"] or 0) < -0.1][:limit]
        return {"improvers": improvers, "decliners": decliners, "has_data": bool(shifts)}
    except Exception as e:
        logger.warning("sentiment shift collection failed: %s", e)
        return {"improvers": [], "decliners": [], "has_data": False}


# ── HTML Rendering ──────────────────────────────────────────────────

def _render_html(data: dict) -> tuple[str, str]:
    """Render the digest. Returns (subject, body_html)."""
    week = _week_key()
    subject = f"Quantive Weekly Digest — {week}"

    # Track record section
    tr = data.get("track_record", {})
    if tr.get("has_data"):
        hr = tr.get("hit_rate")
        hr_color = "#10b981" if (hr or 0) >= 60 else "#f59e0b" if (hr or 0) >= 45 else "#ef4444"
        trend_txt = {
            "calibrated": "<span style='color:#10b981;'>Scores calibrated — higher scores hitting more often.</span>",
            "inverted": "<span style='color:#f59e0b;'>Inverted calibration — treat high scores with caution.</span>",
        }.get(tr.get("calibration_trend"), "")
        tr_html = f"""
        <table role="presentation" width="100%" cellpadding="0" cellspacing="6">
          <tr>
            <td align="center" style="background:#f1f5f9;border-radius:8px;padding:14px;">
              <div style="font-size:26px;font-weight:700;color:{hr_color};">{hr if hr is not None else '—'}%</div>
              <div style="font-size:11px;color:#64748b;text-transform:uppercase;">Hit Rate</div>
            </td>
            <td align="center" style="background:#f1f5f9;border-radius:8px;padding:14px;">
              <div style="font-size:26px;font-weight:700;color:#10b981;">{tr.get('wins', 0)}</div>
              <div style="font-size:11px;color:#64748b;text-transform:uppercase;">Wins</div>
            </td>
            <td align="center" style="background:#f1f5f9;border-radius:8px;padding:14px;">
              <div style="font-size:26px;font-weight:700;color:#ef4444;">{tr.get('losses', 0)}</div>
              <div style="font-size:11px;color:#64748b;text-transform:uppercase;">Losses</div>
            </td>
            <td align="center" style="background:#f1f5f9;border-radius:8px;padding:14px;">
              <div style="font-size:26px;font-weight:700;color:#334155;">{tr.get('total', 0)}</div>
              <div style="font-size:11px;color:#64748b;text-transform:uppercase;">Total</div>
            </td>
          </tr>
        </table>
        {f'<p style="font-size:13px;color:#475569;margin:8px 0 0 0;">{trend_txt}</p>' if trend_txt else ''}"""
    else:
        tr_html = "<p style='color:#64748b;font-size:13px;'>No evaluated signals yet — the track record builds as signals mature past their windows.</p>"

    # Discovery section
    sigs = data.get("discovery", [])
    if sigs:
        sig_rows = "".join(
            f"""<tr>
              <td style="padding:6px 8px;border-bottom:1px solid #e2e8f0;font-weight:600;">{s['symbol']}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #e2e8f0;color:#64748b;font-size:12px;">{s['type']}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #e2e8f0;color:{'#10b981' if s['direction']=='bullish' else '#ef4444'};">{s['direction']}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #e2e8f0;font-weight:600;">{s['strength']}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #e2e8f0;color:#475569;font-size:12px;">{s['claim']}</td>
            </tr>"""
            for s in sigs
        )
        sig_html = f"""
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:8px;">
          <tr style="background:#f8fafc;">
            <th align="left" style="padding:8px;font-size:11px;color:#64748b;text-transform:uppercase;">Symbol</th>
            <th align="left" style="padding:8px;font-size:11px;color:#64748b;text-transform:uppercase;">Type</th>
            <th align="left" style="padding:8px;font-size:11px;color:#64748b;text-transform:uppercase;">Call</th>
            <th align="left" style="padding:8px;font-size:11px;color:#64748b;text-transform:uppercase;">Score</th>
            <th align="left" style="padding:8px;font-size:11px;color:#64748b;text-transform:uppercase;">Claim</th>
          </tr>
          {sig_rows}
        </table>"""
    else:
        sig_html = "<p style='color:#64748b;font-size:13px;'>No discovery signals recorded this week.</p>"

    # Bubble section
    flags = data.get("bubble", [])
    if flags:
        flag_rows = "".join(
            f"""<tr>
              <td style="padding:6px 8px;border-bottom:1px solid #e2e8f0;font-weight:600;">{f['symbol']}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #e2e8f0;color:{'#ef4444' if f['level']=='EXTREME' else '#f97316'};font-weight:700;">{f['score']}/100</td>
              <td style="padding:6px 8px;border-bottom:1px solid #e2e8f0;color:{'#ef4444' if f['level']=='EXTREME' else '#f97316'};">{f['level']}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #e2e8f0;color:#475569;font-size:12px;">{', '.join(f['patterns']) or '—'}</td>
            </tr>"""
            for f in flags
        )
        bubble_html = f"""
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:8px;">
          <tr style="background:#f8fafc;">
            <th align="left" style="padding:8px;font-size:11px;color:#64748b;text-transform:uppercase;">Symbol</th>
            <th align="left" style="padding:8px;font-size:11px;color:#64748b;text-transform:uppercase;">Score</th>
            <th align="left" style="padding:8px;font-size:11px;color:#64748b;text-transform:uppercase;">Level</th>
            <th align="left" style="padding:8px;font-size:11px;color:#64748b;text-transform:uppercase;">Patterns</th>
          </tr>
          {flag_rows}
        </table>"""
    else:
        bubble_html = "<p style='color:#10b981;font-size:13px;'>No high bubble-risk flags this week.</p>"

    # Sentiment shifts section
    sent = data.get("sentiment", {}) or {}
    improvers = sent.get("improvers") or []
    decliners = sent.get("decliners") or []
    if improvers or decliners:
        def _sent_row(s, arrow, color):
            delta = s.get("delta")
            delta_txt = f"{delta:+.2f}" if delta is not None else "new"
            prev_txt = f"{s['prev_mean']:+.2f}" if s.get("prev_mean") is not None else "\u2014"
            return f"""<tr>
              <td style="padding:6px 8px;border-bottom:1px solid #e2e8f0;font-weight:600;">{s['symbol']}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #e2e8f0;color:#475569;">{prev_txt} \u2192 <strong>{s['this_mean']:+.2f}</strong></td>
              <td style="padding:6px 8px;border-bottom:1px solid #e2e8f0;color:{color};font-weight:700;">{arrow} {delta_txt}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #e2e8f0;color:#64748b;font-size:12px;">{s['this_count']} articles</td>
            </tr>"""

        shift_rows = "".join(_sent_row(s, "\u2197", "#10b981") for s in improvers[:4]) + "".join(
            _sent_row(s, "\u2198", "#ef4444") for s in decliners[:4]
        )
        sentiment_html = f"""
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:8px;">
          <tr style="background:#f8fafc;">
            <th align="left" style="padding:8px;font-size:11px;color:#64748b;text-transform:uppercase;">Ticker</th>
            <th align="left" style="padding:8px;font-size:11px;color:#64748b;text-transform:uppercase;">Last Week \u2192 This Week</th>
            <th align="left" style="padding:8px;font-size:11px;color:#64748b;text-transform:uppercase;">Shift</th>
            <th align="left" style="padding:8px;font-size:11px;color:#64748b;text-transform:uppercase;">Coverage</th>
          </tr>
          {shift_rows}
        </table>
        <p style="font-size:11px;color:#94a3b8;margin:6px 0 0 0;">News sentiment scores from \u22121.0 (very negative) to +1.0 (very positive).</p>"""
    else:
        sentiment_html = "<p style='color:#64748b;font-size:13px;'>No significant sentiment shifts detected this week.</p>"

    # Market context
    ctx = data.get("context", {})
    ctx_line = ""
    if ctx:
        parts = []
        if ctx.get("volatility"):
            parts.append(f"{ctx['volatility'].title()} volatility")
        if ctx.get("total_tracked"):
            parts.append(f"{ctx['total_tracked']} assets tracked")
        if parts:
            ctx_line = f"<p style='font-size:13px;color:#475569;margin:0 0 14px 0;'>{' · '.join(parts)}</p>"

    body_html = f"""
    <div style="font-family:Arial,Helvetica,sans-serif;max-width:640px;margin:0 auto;background:#ffffff;">
      <div style="background:#0f172a;color:#e2e8f0;padding:22px 26px;border-radius:8px 8px 0 0;">
        <h1 style="margin:0;font-size:19px;font-weight:700;">Quantive Weekly Digest</h1>
        <div style="font-size:12px;color:#94a3b8;margin-top:4px;">{week} · Automated market intelligence summary</div>
      </div>

      <div style="padding:24px 26px;border:1px solid #e2e8f0;border-top:none;">

        {ctx_line}

        <h2 style="font-size:14px;color:#0f172a;margin:18px 0 10px 0;">Signal Track Record</h2>
        {tr_html}

        <h2 style="font-size:14px;color:#0f172a;margin:22px 0 10px 0;">Top Discovery Signals This Week</h2>
        {sig_html}

        <h2 style="font-size:14px;color:#0f172a;margin:22px 0 10px 0;">Bubble Risk Flags</h2>
        {bubble_html}

        <h2 style="font-size:14px;color:#0f172a;margin:22px 0 10px 0;">News Sentiment Shifts</h2>
        {sentiment_html}

        <div style="margin-top:22px;padding-top:14px;border-top:1px solid #e2e8f0;">
          <p style="font-size:11px;color:#94a3b8;margin:0;">
            Automated analytical output for decision-support purposes only. Does not constitute
            financial advice. Past signal accuracy does not guarantee future results.
          </p>
          <p style="font-size:11px;color:#94a3b8;margin:8px 0 0 0;">
            You're receiving this because weekly digest emails are enabled in your Quantive
            notification settings.
          </p>
        </div>
      </div>
    </div>"""

    return subject, body_html


def _collect_all() -> dict:
    return {
        "week": _week_key(),
        "track_record": _collect_track_record(),
        "discovery": _collect_discovery_signals(),
        "bubble": _collect_bubble_flags(),
        "sentiment": _collect_sentiment_shifts(),
        "context": _collect_market_context(),
    }


def build_digest() -> dict:
    """Collect data and render the digest without sending. For preview/testing."""
    data = _collect_all()
    subject, body_html = _render_html(data)
    sent = data.get("sentiment") or {}
    n_improve = len(sent.get("improvers") or [])
    n_decline = len(sent.get("decliners") or [])
    body_text = (
        f"Quantive Weekly Digest {data['week']} — "
        f"Track record: {data['track_record'].get('hit_rate', '—')}% hit rate "
        f"({data['track_record'].get('wins', 0)}W/{data['track_record'].get('losses', 0)}L). "
        f"Top signals: {len(data['discovery'])}. Bubble flags: {len(data['bubble'])}. "
        f"Sentiment improving: {n_improve}, declining: {n_decline}."
    )
    return {"data": data, "subject": subject, "body_html": body_html, "body_text": body_text}


async def send_weekly_digest(db=None, user=None) -> dict:
    """Build and send the weekly digest.

    Args:
        db: Optional DB session (creates one if absent)
        user: Optional single User to send to; defaults to all opted-in users
    """
    from app.database import SessionLocal
    from app.email_service import EmailMessage, send_email

    owns_db = db is None
    if owns_db:
        db = SessionLocal()

    sent, failed, skipped = 0, 0, 0
    try:
        recipients: list = []
        if user is not None:
            if _is_opted_in(db, user):
                recipients = [user]
            else:
                skipped += 1
        else:
            # All users with weekly_digest enabled
            try:
                from app.models.user_profile import UserProfile

                profiles = (
                    db.query(UserProfile)
                    .filter(UserProfile.compliance_constraints.isnot(None))
                    .all()
                )
                user_ids = []
                for prof in profiles:
                    meta = prof.compliance_constraints if isinstance(prof.compliance_constraints, dict) else {}
                    settings = meta.get("notification_settings") or {}
                    if settings.get("weekly_digest") and settings.get("email_alerts", True):
                        user_ids.append(prof.user_id)
                if user_ids:
                    from app.models import User

                    recipients = db.query(User).filter(User.id.in_(user_ids)).all()
            except Exception as e:
                logger.warning("opt-in query failed: %s", e)

        if not recipients:
            return {"sent": 0, "failed": 0, "skipped": skipped + (0 if user is not None else 1) or 0,
                    "note": "No opted-in recipients. Enable 'Weekly Digest' in notification settings."}

        digest = build_digest()
        week = digest["data"]["week"]

        for u in recipients:
            # Idempotency: skip if already sent this week
            if _last_send_marker.get(u.id) == week and user is None:
                skipped += 1
                continue
            try:
                record = await send_email(EmailMessage(
                    to=[u.email],
                    subject=digest["subject"],
                    body_html=digest["body_html"],
                    body_text=digest["body_text"],
                    tags={"type": "weekly_digest", "week": week},
                ))
                if record.status.value in ("sent", "delivered", "logged"):
                    sent += 1
                    _last_send_marker[u.id] = week
                else:
                    failed += 1
            except Exception as e:
                logger.warning("digest send to %s failed: %s", u.email, e)
                failed += 1

        return {"sent": sent, "failed": failed, "skipped": skipped, "week": week}
    finally:
        if owns_db:
            db.close()


def _is_opted_in(db, user) -> bool:
    try:
        from app.models.user_profile import UserProfile

        prof = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        if prof and isinstance(prof.compliance_constraints, dict):
            settings = prof.compliance_constraints.get("notification_settings") or {}
            return bool(settings.get("weekly_digest")) and settings.get("email_alerts", True)
    except Exception:
        pass
    return False
