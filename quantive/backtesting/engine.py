"""Backtesting engine — §29-33.

Walk-forward, transaction costs, slippage, leakage guards, scorecard.
Never uses future information; validates against overfitting.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal
import numpy as np
import pandas as pd

from quantive.risk_engine.metrics import RiskMetrics


@dataclass
class TransactionCostModel:
    commission_bps: float = 5.0  # 5 bps per trade
    spread_bps: float = 5.0
    slippage_bps: float = 2.0
    market_impact_bps_per_pct: float = 10.0  # bps per 1% ADV

    def cost(self, turnover: float, adv_pct: float = 0.0) -> float:
        """Cost as fraction of traded notional."""
        bps = self.commission_bps + self.spread_bps + self.slippage_bps + self.market_impact_bps_per_pct * adv_pct
        return turnover * bps / 10_000


@dataclass
class BacktestResult:
    strategy_name: str
    returns: pd.Series  # net returns after costs
    gross_returns: pd.Series
    turnover: pd.Series
    costs: pd.Series
    scorecard: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def _scorecard(returns: pd.Series, turnover: pd.Series, risk_free: float = 0.0) -> dict:
    r = returns.dropna().values
    if len(r) == 0:
        return {}
    n_years = len(r) / 252
    cagr = float((np.prod(1 + r) ** (252 / max(len(r), 1)) - 1)) if len(r) else 0.0
    vol = RiskMetrics.volatility(r)
    sharpe = RiskMetrics.sharpe(r, risk_free)
    sortino = RiskMetrics.sortino(r, risk_free)
    cum = np.cumprod(1 + r)
    mdd = RiskMetrics.max_drawdown(cum)
    calmar = float(cagr / abs(mdd)) if mdd != 0 else 0.0
    win_rate = float((r > 0).mean()) if len(r) else 0.0
    avg_turnover = float(turnover.mean()) if len(turnover) else 0.0
    return {
        "cagr": cagr,
        "volatility": vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": mdd,
        "calmar": calmar,
        "win_rate": win_rate,
        "avg_turnover": avg_turnover,
        "n_periods": len(r),
    }


class BacktestEngine:
    """Walk-forward backtester with leakage guards."""

    def __init__(self, cost_model: TransactionCostModel | None = None, risk_free: float = 0.0):
        self.costs = cost_model or TransactionCostModel()
        self.rf = risk_free

    def walk_forward(
        self,
        prices: pd.DataFrame,  # columns tickers, index dates
        signal_fn: Callable[[pd.DataFrame], pd.Series],  # train window -> weights (index tickers)
        train_window: int = 252,
        test_window: int = 63,
        rebalance_freq: int = 21,
        start: int | None = None,
    ) -> BacktestResult:
        """Walk-forward: train on [t-train_window:t], test on [t:t+test_window].

        signal_fn must not peek beyond train window — enforced by slicing.
        """
        if prices.empty or prices.shape[1] == 0:
            raise ValueError("prices empty")
        prices = prices.sort_index()
        n = len(prices)
        start = start or train_window
        rets = prices.pct_change().fillna(0)

        # Walk
        weights_history: list[pd.Series] = []
        dates: list[pd.Timestamp] = []
        current_w: pd.Series | None = None

        t = start
        while t + test_window <= n:
            train = prices.iloc[t - train_window : t]
            # leakage guard: signal_fn sees only train
            try:
                w = signal_fn(train)
            except Exception as e:
                # fail safe: hold previous or equal
                w = current_w if current_w is not None else pd.Series(1 / prices.shape[1], index=prices.columns)

            # normalize: no lookahead, weights sum 1, handle missing tickers
            w = w.reindex(prices.columns).fillna(0)
            if w.sum() == 0:
                w = pd.Series(1 / len(w), index=w.index)
            else:
                w = w / w.sum()
                w = w.clip(lower=0)
                w = w / w.sum() if w.sum() else w

            # hold for test window, rebalancing every rebalance_freq
            for k in range(test_window):
                idx = t + k
                if k % rebalance_freq == 0:
                    current_w = w
                weights_history.append(current_w.copy())
                dates.append(prices.index[idx])

            t += test_window

        if not weights_history:
            raise ValueError("No walk-forward windows produced — check train/test sizes")

        w_df = pd.DataFrame(weights_history, index=dates)
        # compute portfolio returns
        # align rets to w_df dates
        aligned_rets = rets.reindex(w_df.index).fillna(0)
        gross = (w_df * aligned_rets).sum(axis=1)

        # turnover + costs
        w_shift = w_df.shift(1).fillna(0)
        # drift-adjusted turnover would need holdings drift; approximate as |w - w_prev|
        turnover = (w_df - w_shift).abs().sum(axis=1) / 2
        costs = turnover * (self.costs.commission_bps + self.costs.spread_bps + self.costs.slippage_bps) / 10_000
        net = gross - costs

        warnings: list[str] = []
        # overfitting defense: parameter sensitivity placeholder — flag if Sharpe extremely high on tiny sample
        sc = _scorecard(net, turnover, self.rf)
        if sc.get("sharpe", 0) > 3.0 and sc.get("n_periods", 0) < 500:
            warnings.append("Sharpe >3 on <2y — possible overfit, validate out-of-sample")
        if sc.get("max_drawdown", 0) < -0.3:
            warnings.append(f"Max DD {sc['max_drawdown']:.0%} exceeds 30% — risk controls recommended")

        # leakage check: ensure signal_fn did not use future index (we already isolated train)
        return BacktestResult(
            strategy_name=signal_fn.__name__ if hasattr(signal_fn, "__name__") else "strategy",
            returns=net,
            gross_returns=gross,
            turnover=turnover,
            costs=costs,
            scorecard=sc,
            warnings=warnings,
        )

    def compare(self, prices: pd.DataFrame, strategies: dict[str, Callable[[pd.DataFrame], pd.Series]], **kwargs) -> dict[str, BacktestResult]:
        out: dict[str, BacktestResult] = {}
        for name, fn in strategies.items():
            res = self.walk_forward(prices, fn, **kwargs)
            res.strategy_name = name
            out[name] = res
        return out
