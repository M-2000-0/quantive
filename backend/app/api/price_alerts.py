"""
Price Alerts API — Real-time alerts for target prices, RSI thresholds, and custom conditions.

Endpoints:
- GET  /api/alerts — List all user alerts
- POST /api/alerts — Create a new alert
- PUT  /api/alerts/{id} — Update an alert
- DELETE /api/alerts/{id} — Delete an alert
- GET  /api/alerts/check — Check all alerts against current prices
- GET  /api/alerts/history — Get triggered alert history
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.market_data.cache import get_cache
from app.security import get_current_user
from typing import Optional
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User

_optional_bearer = HTTPBearer(auto_error=False)

async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(_optional_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Return the current user if a valid token is provided, else None."""
    if credentials is None:
        return None
    try:
        from app.security import decode_token
        payload = decode_token(credentials.credentials)
        if payload:
            uid = payload.get("sub")
            return db.query(User).filter(User.id == uid).first()
    except Exception:
        pass
    return None

from app.api.trading_intelligence import _fetch_yahoo_quote, _calculate_rsi, _fetch_history

router = APIRouter(prefix="/api/alerts", tags=["price-alerts"])


def _get_user_by_id(user_id: str) -> Optional[User]:
    """Look up a user by id for notification delivery."""
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            return db.query(User).filter(User.id == user_id).first()
        finally:
            db.close()
    except Exception:
        return None

# In-memory alert storage (production: use DB)
_alerts: dict[str, list[dict]] = {}
_alert_history: list[dict] = []
_counter = 0


class AlertCreate(BaseModel):
    symbol: str
    alert_type: str  # "price_above", "price_below", "rsi_overbought", "rsi_oversold", "change_pct"
    threshold: Optional[float] = None  # price target or RSI level
    message: str = ""
    active: bool = True


class AlertResponse(BaseModel):
    id: str
    symbol: str
    alert_type: str
    threshold: Optional[float]
    message: str
    active: bool
    triggered: bool
    current_price: Optional[float] = None
    created_at: str


@router.get("")
def list_alerts(user=Depends(get_optional_user)):
    """List all alerts for the current user."""
    user_id = str(user.id) if user else "default"
    alerts = _alerts.get(user_id, [])
    # Enrich with current prices
    for alert in alerts:
        if alert["alert_type"] in ("price_above", "price_below"):
            quote = _fetch_yahoo_quote(alert["symbol"])
            alert["current_price"] = quote.get("price")
        elif alert["alert_type"] in ("rsi_overbought", "rsi_oversold"):
            history = _fetch_history(alert["symbol"], 30)
            if len(history) >= 15:
                rsi = _calculate_rsi(history)
                alert["current_rsi"] = rsi.get("value")
    return {"alerts": alerts, "count": len(alerts)}


@router.post("", status_code=201)
def create_alert(data: AlertCreate, user=Depends(get_optional_user)):
    """Create a new price alert."""
    global _counter
    _counter += 1
    user_id = str(user.id) if user else "default"

    if user_id not in _alerts:
        _alerts[user_id] = []

    alert = {
        "id": f"alert_{_counter}",
        "symbol": data.symbol.upper(),
        "alert_type": data.alert_type,
        "threshold": data.threshold,
        "message": data.message or _default_message(data),
        "active": data.active,
        "triggered": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    _alerts[user_id].append(alert)
    return alert


@router.put("/{alert_id}")
def update_alert(alert_id: str, data: AlertCreate, user=Depends(get_optional_user)):
    """Update an existing alert."""
    user_id = str(user.id) if user else "default"
    for alert in _alerts.get(user_id, []):
        if alert["id"] == alert_id:
            alert["symbol"] = data.symbol.upper()
            alert["alert_type"] = data.alert_type
            alert["threshold"] = data.threshold
            alert["message"] = data.message or _default_message(data)
            alert["active"] = data.active
            return alert
    raise HTTPException(status_code=404, detail="Alert not found")


@router.delete("/{alert_id}", status_code=204)
def delete_alert(alert_id: str, user=Depends(get_optional_user)):
    """Delete an alert."""
    user_id = str(user.id) if user else "default"
    alerts = _alerts.get(user_id, [])
    _alerts[user_id] = [a for a in alerts if a["id"] != alert_id]
    return None


@router.get("/check")
def check_alerts(user=Depends(get_optional_user)):
    """Check all active alerts against current market conditions.

    Returns triggered alerts with current prices.
    """
    user_id = str(user.id) if user else "default"
    alerts = _alerts.get(user_id, [])
    triggered = []

    for alert in alerts:
        if not alert["active"] or alert["triggered"]:
            continue

        symbol = alert["symbol"]
        alert_type = alert["alert_type"]
        threshold = alert.get("threshold")
        fired = False

        if alert_type == "price_above" and threshold:
            quote = _fetch_yahoo_quote(symbol)
            price = quote.get("price", 0)
            if price and price >= threshold:
                fired = True
                alert["current_price"] = price

        elif alert_type == "price_below" and threshold:
            quote = _fetch_yahoo_quote(symbol)
            price = quote.get("price", 0)
            if price and price <= threshold:
                fired = True
                alert["current_price"] = price

        elif alert_type == "rsi_overbought" and threshold:
            history = _fetch_history(symbol, 30)
            if len(history) >= 15:
                rsi = _calculate_rsi(history)
                if rsi.get("value", 50) >= threshold:
                    fired = True
                    alert["current_rsi"] = rsi.get("value")

        elif alert_type == "rsi_oversold" and threshold:
            history = _fetch_history(symbol, 30)
            if len(history) >= 15:
                rsi = _calculate_rsi(history)
                if rsi.get("value", 50) <= threshold:
                    fired = True
                    alert["current_rsi"] = rsi.get("value")

        elif alert_type == "change_pct" and threshold:
            quote = _fetch_yahoo_quote(symbol)
            change = quote.get("change_pct", 0)
            if abs(change) >= abs(threshold):
                fired = True

        if fired:
            alert["triggered"] = True
            alert["triggered_at"] = datetime.now(timezone.utc).isoformat()
            triggered.append(alert)
            _alert_history.append({
                **alert,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            })

    return {
        "checked": len(alerts),
        "triggered_count": len(triggered),
        "triggered": triggered,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/history")
def get_alert_history(user=Depends(get_optional_user)):
    """Get history of triggered alerts."""
    return {"history": _alert_history[-50:], "count": len(_alert_history)}


def _default_message(data: AlertCreate) -> str:
    """Generate default alert message."""
    sym = data.symbol.upper()
    if data.alert_type == "price_above":
        return f"{sym} price crossed above ${data.threshold}"
    elif data.alert_type == "price_below":
        return f"{sym} price dropped below ${data.threshold}"
    elif data.alert_type == "rsi_overbought":
        return f"{sym} RSI crossed above {data.threshold} (overbought)"
    elif data.alert_type == "rsi_oversold":
        return f"{sym} RSI dropped below {data.threshold} (oversold)"
    elif data.alert_type == "change_pct":
        return f"{sym} moved more than {data.threshold}%"
    return f"Alert on {sym}"


# ── Background Alert Checker ─────────────────────────────────────────

import asyncio
import logging

logger = logging.getLogger("quantive.alerts")
_bg_task = None


async def _background_check_loop():
    """Periodically check all alerts and push via WebSocket when triggered."""
    while True:
        try:
            await asyncio.sleep(60)  # Check every 60 seconds
            for user_id, alerts in list(_alerts.items()):
                for alert in alerts:
                    if not alert["active"] or alert["triggered"]:
                        continue
                    symbol = alert["symbol"]
                    alert_type = alert["alert_type"]
                    threshold = alert.get("threshold")
                    fired = False
                    try:
                        if alert_type == "price_above" and threshold:
                            quote = _fetch_yahoo_quote(symbol)
                            price = quote.get("price", 0)
                            if price and price >= threshold:
                                fired = True
                                alert["current_price"] = price
                        elif alert_type == "price_below" and threshold:
                            quote = _fetch_yahoo_quote(symbol)
                            price = quote.get("price", 0)
                            if price and price <= threshold:
                                fired = True
                                alert["current_price"] = price
                        elif alert_type == "rsi_overbought" and threshold:
                            history = _fetch_history(symbol, 30)
                            if len(history) >= 15:
                                rsi = _calculate_rsi(history)
                                if rsi.get("value", 50) >= threshold:
                                    fired = True
                                    alert["current_rsi"] = rsi.get("value")
                        elif alert_type == "rsi_oversold" and threshold:
                            history = _fetch_history(symbol, 30)
                            if len(history) >= 15:
                                rsi = _calculate_rsi(history)
                                if rsi.get("value", 50) <= threshold:
                                    fired = True
                                    alert["current_rsi"] = rsi.get("value")
                        elif alert_type == "change_pct" and threshold:
                            quote = _fetch_yahoo_quote(symbol)
                            change = quote.get("change_pct", 0)
                            if abs(change) >= abs(threshold):
                                fired = True
                    except Exception as e:
                        logger.debug(f"Alert check error for {symbol}: {e}")

                    if fired:
                        alert["triggered"] = True
                        alert["triggered_at"] = datetime.now(timezone.utc).isoformat()
                        _alert_history.append({**alert, "checked_at": datetime.now(timezone.utc).isoformat()})

                        # Multi-channel delivery (WebSocket + email + SMS)
                        try:
                            from app.services.notification_dispatcher import (
                                send_price_alert,
                                should_notify,
                            )
                            user = _get_user_by_id(user_id)
                            email_on = alert.get("notify_email", True)
                            sms_on = alert.get("notify_sms", False)
                            if user and should_notify(user_id, f"price:{symbol}:{alert_type}"):
                                await send_price_alert(
                                    user_id=user_id,
                                    user_email=user.email if email_on else "",
                                    symbol=symbol,
                                    alert_type=alert_type,
                                    message=alert.get("message") or f"Alert triggered for {symbol}",
                                    current_price=alert.get("current_price"),
                                    threshold=threshold,
                                    user_phone=(getattr(user, "phone", None) or getattr(user, "phone_number", None)) if sms_on else None,
                                    notify_email=email_on,
                                    notify_sms=sms_on,
                                )
                        except Exception as e:
                            logger.debug("Notification dispatch failed: %s", e)

                        # Push via WebSocket (legacy direct push, kept as fallback)
                        try:
                            from app.websocket import get_ws_manager
                            manager = get_ws_manager()
                            import asyncio as _asyncio
                            await manager.send_to_user(user_id, {
                                "type": "alert_triggered",
                                "alert_id": alert["id"],
                                "symbol": symbol,
                                "alert_type": alert_type,
                                "message": alert["message"],
                                "current_price": alert.get("current_price"),
                                "current_rsi": alert.get("current_rsi"),
                                "threshold": threshold,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            })
                        except Exception as e:
                            logger.debug(f"WebSocket push failed: {e}")
        except Exception as e:
            logger.error(f"Background alert check error: {e}")


def start_alert_checker():
    """Start the background alert checker task."""
    global _bg_task
    if _bg_task is None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                _bg_task = loop.create_task(_background_check_loop())
                logger.info("Background alert checker started")
            else:
                logger.warning("No running event loop, alert checker not started")
        except Exception as e:
            logger.warning(f"Could not start alert checker: {e}")
