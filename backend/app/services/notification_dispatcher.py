"""Multi-channel notification delivery for market alerts.

Channels:
- Email: uses the existing app.email_service provider stack (SendGrid/Resend/log-only)
- SMS: Twilio REST API when TWILIO_* env vars are configured; otherwise logs only
- WebSocket push: via the existing ConnectionManager (always attempted)

Dispatch is fire-and-forget safe: failures are logged, never raised, so alert
evaluation loops never break because a provider is down.
"""
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger("quantive.notifications")

# In-memory delivery log (last N notifications) for the /history endpoint
_delivery_log: list[dict] = []
_MAX_LOG = 500

# Per-user cooldown so a flapping threshold doesn't spam the inbox
_last_sent: dict[str, float] = {}
_COOLDOWN_SECONDS = 900  # 15 min per user+alert key


# ── Email ───────────────────────────────────────────────────────────

async def _send_email(to: str, subject: str, body_html: str, body_text: str, tags: dict) -> bool:
    try:
        from app.email_service import EmailMessage, send_email
        record = await send_email(EmailMessage(
            to=[to],
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            tags=tags,
        ))
        ok = record.status.value in ("sent", "delivered", "logged")
        if not ok:
            logger.warning("Email delivery %s: %s", record.status.value, record.error)
        return ok
    except Exception as e:
        logger.warning("Email send failed: %s", e)
        return False


# ── SMS (Twilio) ────────────────────────────────────────────────────

async def _send_sms(phone: str, message: str) -> bool:
    sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    token = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_num = os.getenv("TWILIO_FROM_NUMBER", "")
    if not (sid and token and from_num):
        logger.info("SMS skipped (Twilio not configured): would send to %s: %s", phone, message[:80])
        return False
    try:
        # Use Twilio REST API directly via httpx/aiohttp to avoid a hard dependency
        import base64
        import urllib.parse

        try:
            import httpx
            client = httpx.AsyncClient(timeout=10)
            resp = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                headers={"Authorization": "Basic " + base64.b64encode(f"{sid}:{token}".encode()).decode()},
                data={
                    "From": from_num,
                    "To": phone,
                    "Body": message[:1600],  # Twilio limit headroom
                },
            )
            await client.aclose()
            return resp.status_code in (200, 201)
        except ImportError:
            # Fallback: urllib in a thread (sync-safe enough for fire-and-forget)
            import asyncio
            import urllib.request

            def _post():
                data = urllib.parse.urlencode({
                    "From": from_num, "To": phone, "Body": message[:1600],
                }).encode()
                req = urllib.request.Request(
                    f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                    data=data,
                    headers={"Authorization": "Basic " + base64.b64encode(f"{sid}:{token}".encode()).decode()},
                )
                return urllib.request.urlopen(req, timeout=10).status

            status = await asyncio.get_running_loop().run_in_executor(None, _post)
            return status in (200, 201)
    except Exception as e:
        logger.warning("SMS send failed: %s", e)
        return False


# ── WebSocket push ──────────────────────────────────────────────────

async def _push_websocket(user_id: str, payload: dict) -> bool:
    try:
        from app.websocket import get_ws_manager
        manager = get_ws_manager()
        sent = await manager.send_to_user(user_id, payload)
        return sent > 0
    except Exception as e:
        logger.debug("WebSocket push failed for %s: %s", user_id, e)
        return False


# ── Public API ──────────────────────────────────────────────────────

def _log(channel_results: dict, payload: dict, user_id: str):
    _delivery_log.append({
        "user_id": user_id,
        "payload": payload,
        "channels": channel_results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    if len(_delivery_log) > _MAX_LOG:
        del _delivery_log[: len(_delivery_log) - _MAX_LOG]


def should_notify(user_id: str, alert_key: str, cooldown: int = _COOLDOWN_SECONDS) -> bool:
    """Check cooldown gate for a user+alert combination."""
    key = f"{user_id}:{alert_key}"
    now = datetime.now(timezone.utc).timestamp()
    last = _last_sent.get(key, 0)
    if now - last < cooldown:
        return False
    _last_sent[key] = now
    return True


async def send_price_alert(
    user_id: str,
    user_email: str,
    symbol: str,
    alert_type: str,
    message: str,
    current_price: float | None = None,
    threshold: float | None = None,
    user_phone: str | None = None,
    notify_email: bool = True,
    notify_sms: bool = False,
) -> dict:
    """Deliver a price-threshold alert through all configured channels."""
    payload = {
        "type": "alert_triggered",
        "alert_key": f"price:{symbol}:{alert_type}",
        "symbol": symbol,
        "alert_type": alert_type,
        "message": message,
        "current_price": current_price,
        "threshold": threshold,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    results = {"websocket": await _push_websocket(user_id, payload)}

    if notify_email and user_email:
        subject = f"Quantive Alert: {symbol} — {message}"
        body_html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
          <div style="background:#0f172a;color:#e2e8f0;padding:20px;border-radius:8px 8px 0 0;">
            <h1 style="margin:0;font-size:18px;">Market Alert</h1>
          </div>
          <div style="background:#f8fafc;padding:20px;border:1px solid #e2e8f0;border-top:none;">
            <p style="font-size:16px;margin:0 0 8px 0;"><strong>{symbol}</strong> — {message}</p>
            {f'<p style="color:#475569;">Current price: <strong>{current_price}</strong></p>' if current_price is not None else ''}
            {f'<p style="color:#475569;">Threshold: {threshold}</p>' if threshold is not None else ''}
            <p style="color:#94a3b8;font-size:12px;margin-top:16px;">
              Automated analytical output for decision-support purposes only.
              Not financial advice.
            </p>
          </div>
        </div>"""
        results["email"] = await _send_email(
            user_email, subject, body_html,
            f"{symbol}: {message}" + (f" (current: {current_price})" if current_price is not None else ""),
            tags={"type": "price_alert", "symbol": symbol},
        )

    if notify_sms and user_phone:
        sms_text = f"Quantive: {symbol} — {message}"
        if current_price is not None:
            sms_text += f" (now {current_price})"
        results["sms"] = await _send_sms(user_phone, sms_text)

    _log(results, payload, user_id)
    return results


async def send_bubble_alert(
    user_id: str,
    user_email: str,
    symbol: str,
    asset_name: str,
    risk_score: int,
    risk_level: str,
    patterns: list[str],
    indicators: list[str],
    user_phone: str | None = None,
    notify_email: bool = True,
    notify_sms: bool = False,
) -> dict:
    """Deliver a bubble-risk alert through all configured channels."""
    pattern_str = ", ".join(patterns[:3]) if patterns else "none"
    top_indicators = [i.get("name", str(i)) if isinstance(i, dict) else str(i) for i in indicators[:4]]
    indicator_str = ", ".join(top_indicators)

    payload = {
        "type": "bubble_alert",
        "alert_key": f"bubble:{symbol}",
        "symbol": symbol,
        "asset_name": asset_name,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "patterns": patterns,
        "indicators": top_indicators,
        "message": f"{asset_name} ({symbol}) flagged {risk_level} bubble risk ({risk_score}/100)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    results = {"websocket": await _push_websocket(user_id, payload)}

    if notify_email and user_email:
        color = {"critical": "#dc2626", "high": "#ea580c", "elevated": "#d97706", "moderate": "#ca8a04"}.get(
            risk_level.lower(), "#64748b"
        )
        subject = f"Quantive Bubble Alert: {symbol} flagged {risk_level} risk ({risk_score}/100)"
        body_html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
          <div style="background:{color};color:white;padding:20px;border-radius:8px 8px 0 0;">
            <h1 style="margin:0;font-size:18px;">Bubble Risk Alert — {risk_level.title()}</h1>
          </div>
          <div style="background:#f8fafc;padding:20px;border:1px solid #e2e8f0;border-top:none;">
            <p style="font-size:16px;margin:0 0 12px 0;">
              <strong>{asset_name} ({symbol})</strong> scored <strong>{risk_score}/100</strong>
              on the bubble risk detector.
            </p>
            <p style="margin:0 0 6px 0;"><strong>Patterns detected:</strong> {pattern_str}</p>
            <p style="margin:0 0 6px 0;"><strong>Key indicators:</strong> {indicator_str}</p>
            <p style="color:#94a3b8;font-size:12px;margin-top:16px;">
              Automated analytical output for decision-support purposes only.
              This is not a recommendation to buy or sell.
            </p>
          </div>
        </div>"""
        results["email"] = await _send_email(
            user_email, subject, body_html,
            f"Bubble alert: {asset_name} ({symbol}) risk {risk_score}/100 [{risk_level}] — {pattern_str}",
            tags={"type": "bubble_alert", "symbol": symbol, "risk_level": risk_level},
        )

    if notify_sms and user_phone:
        sms_text = f"Quantive bubble alert: {symbol} risk {risk_score}/100 ({risk_level}). Patterns: {pattern_str}"
        results["sms"] = await _send_sms(user_phone, sms_text)

    _log(results, payload, user_id)
    return results


def get_delivery_history(limit: int = 50) -> list[dict]:
    """Recent notification deliveries for the settings/history UI."""
    return _delivery_log[-limit:][::-1]


def is_sms_configured() -> bool:
    return bool(
        os.getenv("TWILIO_ACCOUNT_SID")
        and os.getenv("TWILIO_AUTH_TOKEN")
        and os.getenv("TWILIO_FROM_NUMBER")
    )
