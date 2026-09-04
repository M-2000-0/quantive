"""
Backtesting Engine API — Test trading strategies against historical data.

Provides:
- Strategy backtesting with configurable parameters
- Performance metrics: Sharpe ratio, max drawdown, CAGR, win rate
- Multiple strategy types: SMA crossover, RSI mean reversion, momentum
- Comparison of strategies
"""
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.trading_intelligence import (
    _calculate_rsi,
    _calculate_macd,
    _calculate_moving_averages,
    _fetch_history,
)
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


router = APIRouter(prefix="/api/backtest", tags=["backtesting"])


class BacktestRequest(BaseModel):
    symbol: str
    strategy: str  # "sma_crossover", "rsi_reversal", "macd", "momentum"
    initial_capital: float = 10000.0
    days: int = 365
    # SMA crossover params
    fast_period: int = 20
    slow_period: int = 50
    # RSI params
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    # General
    position_size_pct: float = 100.0  # % of capital per trade


@router.post("/run")
def run_backtest(data: BacktestRequest, user=Depends(get_optional_user)):
    """Run a backtest on a trading strategy.

    Returns trades, performance metrics, and equity curve.
    """
    history = _fetch_history(data.symbol.upper(), data.days)
    if len(history) < 50:
        raise HTTPException(status_code=400, detail="Insufficient historical data for this analysis")

    prices = np.array(history, dtype=float)
    strategy = data.strategy

    if strategy == "sma_crossover":
        signals = _sma_crossover_signals(prices, data.fast_period, data.slow_period)
    elif strategy == "rsi_reversal":
        signals = _rsi_reversal_signals(prices, data.rsi_period, data.rsi_oversold, data.rsi_overbought)
    elif strategy == "macd":
        signals = _macd_signals(prices)
    elif strategy == "momentum":
        signals = _momentum_signals(prices)
    else:
        raise HTTPException(status_code=400, detail="Unknown strategy")

    # Simulate trades
    result = _simulate_trades(prices, signals, data.initial_capital, data.position_size_pct)

    return {
        "symbol": data.symbol.upper(),
        "strategy": strategy,
        "period_days": data.days,
        "price_data": [round(p, 2) for p in history],
        "signals": signals,
        "trades": result["trades"],
        "metrics": result["metrics"],
        "equity_curve": result["equity_curve"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/strategies")
def list_strategies(user=Depends(get_optional_user)):
    """List available backtesting strategies."""
    return {
        "strategies": [
            {
                "id": "sma_crossover",
                "name": "SMA Crossover",
                "description": "Buy when fast MA crosses above slow MA, sell on cross below",
                "params": ["fast_period", "slow_period"],
                "difficulty": "beginner",
            },
            {
                "id": "rsi_reversal",
                "name": "RSI Mean Reversion",
                "description": "Buy when RSI drops below oversold, sell when above overbought",
                "params": ["rsi_period", "rsi_oversold", "rsi_overbought"],
                "difficulty": "intermediate",
            },
            {
                "id": "macd",
                "name": "MACD Crossover",
                "description": "Buy on MACD bullish crossover, sell on bearish crossover",
                "params": [],
                "difficulty": "intermediate",
            },
            {
                "id": "momentum",
                "name": "Price Momentum",
                "description": "Buy on positive momentum (price above 20-day high), sell on negative",
                "params": [],
                "difficulty": "advanced",
            },
        ]
    }


@router.get("/compare")
def compare_strategies(
    symbol: str = Query("SPY"),
    days: int = Query(365, ge=30, le=730),
    initial_capital: float = Query(10000),
    user=Depends(get_optional_user),
):
    """Compare all strategies on the same symbol."""
    history = _fetch_history(symbol.upper(), days)
    if len(history) < 50:
        raise HTTPException(status_code=400, detail=f"Insufficient data for {symbol}")

    prices = np.array(history, dtype=float)
    results = []

    for strat_id, strat_fn in [
        ("sma_crossover", lambda p: _sma_crossover_signals(p, 20, 50)),
        ("rsi_reversal", lambda p: _rsi_reversal_signals(p, 14, 30, 70)),
        ("macd", _macd_signals),
        ("momentum", _momentum_signals),
    ]:
        signals = strat_fn(prices)
        result = _simulate_trades(prices, signals, initial_capital, 100.0)
        results.append({
            "strategy": strat_id,
            "metrics": result["metrics"],
        })

    # Sort by Sharpe ratio
    results.sort(key=lambda x: x["metrics"].get("sharpe_ratio", 0), reverse=True)

    return {
        "symbol": symbol.upper(),
        "days": days,
        "comparison": results,
        "best_strategy": results[0]["strategy"] if results else None,
    }


# ── Signal Generators ────────────────────────────────────────────────

def _sma_crossover_signals(prices: np.ndarray, fast: int, slow: int) -> list[dict]:
    """Generate SMA crossover buy/sell signals."""
    signals = []
    for i in range(slow, len(prices)):
        fast_ma = np.mean(prices[i - fast:i])
        slow_ma = np.mean(prices[i - slow:i])
        prev_fast = np.mean(prices[i - fast - 1:i - 1])
        prev_slow = np.mean(prices[i - slow - 1:i - 1])

        signal = "HOLD"
        if prev_fast <= prev_slow and fast_ma > slow_ma:
            signal = "BUY"
        elif prev_fast >= prev_slow and fast_ma < slow_ma:
            signal = "SELL"

        signals.append({
            "index": i,
            "signal": signal,
            "fast_ma": round(float(fast_ma), 2),
            "slow_ma": round(float(slow_ma), 2),
        })
    return signals


def _rsi_reversal_signals(prices: np.ndarray, period: int, oversold: float, overbought: float) -> list[dict]:
    """Generate RSI mean reversion signals."""
    signals = []
    for i in range(period + 1, len(prices)):
        rsi = _calculate_rsi(prices[:i + 1].tolist(), period)
        rsi_val = rsi.get("value", 50)
        prev_rsi = _calculate_rsi(prices[:i].tolist(), period).get("value", 50)

        signal = "HOLD"
        if prev_rsi >= oversold and rsi_val < oversold:
            signal = "BUY"
        elif prev_rsi <= overbought and rsi_val > overbought:
            signal = "SELL"

        signals.append({"index": i, "signal": signal, "rsi": rsi_val})
    return signals


def _macd_signals(prices: np.ndarray) -> list[dict]:
    """Generate MACD crossover signals."""
    signals = []
    if len(prices) < 26:
        return signals

    def ema(data, period):
        alpha = 2 / (period + 1)
        result = np.zeros_like(data)
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
        return result

    ema12 = ema(prices, 12)
    ema26 = ema(prices, 26)
    macd_line = ema12 - ema26
    signal_line = ema(macd_line, 9)

    for i in range(27, len(prices)):
        prev_diff = macd_line[i - 1] - signal_line[i - 1]
        curr_diff = macd_line[i] - signal_line[i]

        signal = "HOLD"
        if prev_diff <= 0 and curr_diff > 0:
            signal = "BUY"
        elif prev_diff >= 0 and curr_diff < 0:
            signal = "SELL"

        signals.append({
            "index": i,
            "signal": signal,
            "macd": round(float(macd_line[i]), 4),
            "signal_line": round(float(signal_line[i]), 4),
        })
    return signals


def _momentum_signals(prices: np.ndarray, lookback: int = 20) -> list[dict]:
    """Generate momentum signals (buy on 20-day high, sell on 20-day low)."""
    signals = []
    for i in range(lookback, len(prices)):
        window = prices[i - lookback:i]
        high = np.max(window)
        low = np.min(window)
        current = prices[i]

        signal = "HOLD"
        if current > high:
            signal = "BUY"
        elif current < low:
            signal = "SELL"

        signals.append({
            "index": i,
            "signal": signal,
            "high_20d": round(float(high), 2),
            "low_20d": round(float(low), 2),
        })
    return signals


# ── Trade Simulator ──────────────────────────────────────────────────

def _simulate_trades(prices: np.ndarray, signals: list, initial_capital: float, position_pct: float) -> dict:
    """Simulate trades based on signals and calculate metrics."""
    capital = initial_capital
    shares = 0.0
    trades = []
    equity_curve = [{"day": 0, "equity": initial_capital}]
    in_position = False

    for sig in signals:
        idx = sig["index"]
        price = prices[idx]
        sig_type = sig["signal"]

        if sig_type == "BUY" and not in_position:
            invest = capital * (position_pct / 100)
            shares = invest / price
            capital -= invest
            in_position = True
            trades.append({
                "type": "BUY",
                "day": idx,
                "price": round(float(price), 2),
                "shares": round(shares, 4),
                "value": round(float(invest), 2),
            })

        elif sig_type == "SELL" and in_position:
            proceeds = shares * price
            capital += proceeds
            pnl = proceeds - trades[-1]["value"] if trades else 0
            trades.append({
                "type": "SELL",
                "day": idx,
                "price": round(float(price), 2),
                "shares": round(shares, 4),
                "value": round(float(proceeds), 2),
                "pnl": round(float(pnl), 2),
                "pnl_pct": round(float(pnl / trades[-1]["value"] * 100), 2) if trades and trades[-1]["value"] > 0 else 0,
            })
            shares = 0.0
            in_position = False

        equity = capital + (shares * price if in_position else 0)
        equity_curve.append({"day": idx, "equity": round(float(equity), 2)})

    # Final position value
    final_price = prices[-1]
    final_equity = capital + (shares * final_price if in_position else 0)

    # Calculate metrics
    metrics = _calculate_metrics(
        initial_capital, final_equity, equity_curve, trades, len(prices)
    )

    return {"trades": trades, "equity_curve": equity_curve, "metrics": metrics}


def _calculate_metrics(initial: float, final: float, equity_curve: list, trades: list, total_days: int) -> dict:
    """Calculate performance metrics."""
    # Total return
    total_return_pct = ((final - initial) / initial * 100) if initial > 0 else 0

    # CAGR
    years = total_days / 365.25
    cagr = ((final / initial) ** (1 / years) - 1) * 100 if years > 0 and initial > 0 else 0

    # Sharpe ratio (daily returns)
    equities = [e["equity"] for e in equity_curve]
    if len(equities) > 1:
        daily_returns = np.diff(equities) / np.array(equities[:-1])
        avg_return = np.mean(daily_returns)
        std_return = np.std(daily_returns) if np.std(daily_returns) > 0 else 0.001
        sharpe = (avg_return / std_return) * np.sqrt(252)  # Annualized
    else:
        sharpe = 0

    # Max drawdown
    peak = equities[0]
    max_dd = 0
    for eq in equities:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100
        if dd > max_dd:
            max_dd = dd

    # Win rate
    winning_trades = [t for t in trades if t.get("pnl", 0) > 0]
    sell_trades = [t for t in trades if t["type"] == "SELL"]
    win_rate = (len(winning_trades) / len(sell_trades) * 100) if sell_trades else 0

    # Average win/loss
    avg_win = np.mean([t["pnl"] for t in winning_trades]) if winning_trades else 0
    losing_trades = [t for t in sell_trades if t.get("pnl", 0) <= 0]
    avg_loss = np.mean([abs(t["pnl"]) for t in losing_trades]) if losing_trades else 0

    return {
        "initial_capital": round(initial, 2),
        "final_value": round(final, 2),
        "total_return_pct": round(total_return_pct, 2),
        "cagr": round(cagr, 2),
        "sharpe_ratio": round(float(sharpe), 2),
        "max_drawdown_pct": round(max_dd, 2),
        "total_trades": len(sell_trades) * 2,
        "win_rate_pct": round(win_rate, 1),
        "avg_win": round(float(avg_win), 2),
        "avg_loss": round(float(avg_loss), 2),
        "profit_factor": round(float(avg_win / avg_loss), 2) if avg_loss > 0 else 0,
    }
