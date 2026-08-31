"""Broker abstraction — §43.

All brokers share one interface so Quantive can support multiple regulated providers
without rewriting the portfolio engine. Paper trading is first-class §44.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
from enum import Enum


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


@dataclass
class Order:
    id: str
    ticker: str
    side: OrderSide
    quantity: float
    order_type: OrderType = OrderType.MARKET
    limit_price: float | None = None
    status: Literal["pending", "filled", "cancelled", "rejected"] = "pending"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    filled_at: datetime | None = None
    filled_price: float | None = None


@dataclass
class Position:
    ticker: str
    quantity: float
    avg_price: float
    market_price: float | None = None


@dataclass
class Account:
    cash: float
    equity: float
    buying_power: float
    currency: str = "USD"


class Broker(ABC):
    """Abstract broker — §43."""

    @abstractmethod
    def get_account(self) -> Account: ...

    @abstractmethod
    def get_positions(self) -> list[Position]: ...

    @abstractmethod
    def get_orders(self) -> list[Order]: ...

    @abstractmethod
    def place_order(self, ticker: str, side: OrderSide, quantity: float, order_type: OrderType = OrderType.MARKET, limit_price: float | None = None) -> Order: ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool: ...

    @abstractmethod
    def get_market_price(self, ticker: str) -> float | None: ...


class PaperBroker(Broker):
    """Deterministic paper trading broker — §44. No real money, full audit."""

    def __init__(self, initial_cash: float = 100_000.0):
        self._cash = initial_cash
        self._initial = initial_cash
        self._positions: dict[str, Position] = {}
        self._orders: dict[str, Order] = {}
        self._prices: dict[str, float] = {}
        self._next_id = 1

    def set_market_price(self, ticker: str, price: float) -> None:
        self._prices[ticker.upper()] = float(price)

    def get_account(self) -> Account:
        equity = self._cash + sum(p.quantity * (self._prices.get(p.ticker, p.avg_price)) for p in self._positions.values())
        return Account(cash=self._cash, equity=equity, buying_power=self._cash)

    def get_positions(self) -> list[Position]:
        for p in self._positions.values():
            p.market_price = self._prices.get(p.ticker)
        return list(self._positions.values())

    def get_orders(self) -> list[Order]:
        return list(self._orders.values())

    def get_market_price(self, ticker: str) -> float | None:
        return self._prices.get(ticker.upper())

    def place_order(self, ticker: str, side: OrderSide, quantity: float, order_type: OrderType = OrderType.MARKET, limit_price: float | None = None) -> Order:
        ticker = ticker.upper()
        price = self._prices.get(ticker)
        if price is None:
            raise ValueError(f"No market price for {ticker} — set via set_market_price() or stale-price guard will reject")
        # safety: market order uses market price, limit respects limit_price
        fill_price = limit_price if (order_type == OrderType.LIMIT and limit_price is not None) else price
        oid = f"paper-{self._next_id}"
        self._next_id += 1
        order = Order(id=oid, ticker=ticker, side=side, quantity=quantity, order_type=order_type, limit_price=limit_price, status="filled", filled_at=datetime.now(timezone.utc), filled_price=fill_price)
        self._orders[oid] = order
        # update positions + cash
        if side == OrderSide.BUY:
            cost = quantity * fill_price
            if cost > self._cash + 1e-9:
                order.status = "rejected"
                raise ValueError(f"Insufficient cash: need {cost:.2f}, have {self._cash:.2f}")
            self._cash -= cost
            pos = self._positions.get(ticker)
            if pos:
                total_qty = pos.quantity + quantity
                pos.avg_price = (pos.quantity * pos.avg_price + quantity * fill_price) / total_qty
                pos.quantity = total_qty
            else:
                self._positions[ticker] = Position(ticker=ticker, quantity=quantity, avg_price=fill_price)
        else:
            pos = self._positions.get(ticker)
            if not pos or pos.quantity < quantity - 1e-9:
                order.status = "rejected"
                raise ValueError(f"Insufficient position for {ticker}: have {pos.quantity if pos else 0}, sell {quantity}")
            pos.quantity -= quantity
            self._cash += quantity * fill_price
            if pos.quantity <= 1e-9:
                del self._positions[ticker]
        return order

    def cancel_order(self, order_id: str) -> bool:
        o = self._orders.get(order_id)
        if not o or o.status != "pending":
            return False
        o.status = "cancelled"
        return True
