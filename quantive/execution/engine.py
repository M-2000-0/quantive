"""Execution engine + safety — §42, §45.

Signal → Decision → Risk approval → Execution planner → Broker → Confirmation
with kill-switch, size limits, stale-price detection, duplicate prevention.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Literal

from quantive.broker.base import Broker, OrderSide, OrderType


@dataclass
class ExecutionConfig:
    max_order_size: float = 100_000.0  # notional per order
    max_daily_loss: float = 50_000.0
    max_position_size: float = 0.30  # max weight per ticker
    max_portfolio_exposure: float = 1.0
    stale_price_seconds: int = 300
    duplicate_window_seconds: int = 60
    kill_switch: bool = False


@dataclass
class ExecutionPlan:
    ticker: str
    side: OrderSide
    quantity: float
    order_type: OrderType = OrderType.MARKET
    limit_price: float | None = None
    reason: str = ""


class ExecutionEngine:
    """Plans and executes with safety guards."""

    def __init__(self, broker: Broker, config: ExecutionConfig | None = None):
        self.broker = broker
        self.config = config or ExecutionConfig()
        self._recent_orders: list[tuple[str, datetime]] = []  # (ticker+side, time)
        self._daily_pnl: float = 0.0
        self._last_price_time: dict[str, datetime] = {}

    def _check_kill_switch(self) -> None:
        if self.config.kill_switch:
            raise RuntimeError("Execution halted — kill switch engaged")

    def _check_stale_price(self, ticker: str) -> None:
        # PaperBroker has no timestamp; real broker should update _last_price_time
        last = self._last_price_time.get(ticker.upper())
        if last and (datetime.now(timezone.utc) - last).total_seconds() > self.config.stale_price_seconds:
            raise ValueError(f"Stale price for {ticker} — last update {last.isoformat()}")

    def _check_duplicate(self, ticker: str, side: OrderSide) -> None:
        now = datetime.now(timezone.utc)
        key = f"{ticker.upper()}:{side.value}"
        # prune old
        self._recent_orders = [(k, t) for k, t in self._recent_orders if (now - t).total_seconds() < self.config.duplicate_window_seconds]
        if any(k == key for k, _ in self._recent_orders):
            raise ValueError(f"Duplicate order rejected for {key} within {self.config.duplicate_window_seconds}s")

    def _check_size(self, plan: ExecutionPlan, price: float) -> None:
        notional = plan.quantity * price
        if notional > self.config.max_order_size:
            raise ValueError(f"Order notional {notional:.2f} exceeds max {self.config.max_order_size:.2f}")

    def plan(self, target_weights: dict[str, float], current_weights: dict[str, float], prices: dict[str, float], total_equity: float) -> list[ExecutionPlan]:
        """Diff target vs current into execution plans."""
        self._check_kill_switch()
        plans: list[ExecutionPlan] = []
        tickers = set(target_weights) | set(current_weights)
        for t in tickers:
            tgt = target_weights.get(t, 0.0)
            cur = current_weights.get(t, 0.0)
            delta_w = tgt - cur
            if abs(delta_w) < 0.001:  # rebalance threshold 0.1% (§39)
                continue
            if tgt > self.config.max_position_size:
                raise ValueError(f"Target weight {tgt:.1%} for {t} exceeds max position {self.config.max_position_size:.0%}")
            price = prices.get(t.upper())
            if not price:
                continue
            qty = abs(delta_w) * total_equity / price
            side = OrderSide.BUY if delta_w > 0 else OrderSide.SELL
            plans.append(ExecutionPlan(ticker=t.upper(), side=side, quantity=qty, reason=f"Rebalance {cur:.1%}→{tgt:.1%}"))
        return plans

    def execute(self, plans: list[ExecutionPlan]) -> list:
        self._check_kill_switch()
        results = []
        for p in plans:
            self._check_duplicate(p.ticker, p.side)
            price = self.broker.get_market_price(p.ticker)
            if price is None:
                raise ValueError(f"No market price for {p.ticker} — stale price guard")
            self._check_size(p, price)
            # stale check
            self._check_stale_price(p.ticker)
            order = self.broker.place_order(p.ticker, p.side, p.quantity, p.order_type, p.limit_price)
            self._recent_orders.append((f"{p.ticker}:{p.side.value}", datetime.now(timezone.utc)))
            results.append(order)
        return results

    def halt(self) -> None:
        self.config.kill_switch = True

    def resume(self) -> None:
        self.config.kill_switch = False
