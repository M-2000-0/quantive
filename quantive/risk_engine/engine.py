"""Risk engine — aggregates metrics into a report."""
from __future__ import annotations

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from quantive.risk_engine.metrics import RiskMetrics


class RiskReport(BaseModel):
    volatility: float = 0.0
    downside_deviation: float = 0.0
    sharpe: float = 0.0
    sortino: float = 0.0
    max_drawdown: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    beta: float = 0.0
    concentration: dict = Field(default_factory=dict)
    factor_exposure: dict = Field(default_factory=dict)
    liquidity_note: str = ""
    warnings: list[str] = Field(default_factory=list)


class RiskEngine:
    """Compute full risk report for a portfolio's return series."""

    def __init__(self, risk_free_rate: float = 0.02):
        self.rf = risk_free_rate

    def evaluate(
        self,
        returns: np.ndarray | pd.Series,
        market_returns: np.ndarray | pd.Series | None = None,
        weights: np.ndarray | None = None,
        factor_loadings: dict | None = None,
    ) -> RiskReport:
        r = np.asarray(returns, dtype=float).ravel()
        r = r[np.isfinite(r)]
        if len(r) == 0:
            return RiskReport(warnings=["No valid returns"])

        # portfolio cumulative for DD
        cum = np.cumprod(1 + r)
        report = RiskReport(
            volatility=RiskMetrics.volatility(r),
            downside_deviation=RiskMetrics.downside_deviation(r),
            sharpe=RiskMetrics.sharpe(r, self.rf),
            sortino=RiskMetrics.sortino(r, self.rf),
            max_drawdown=RiskMetrics.max_drawdown(cum),
            var_95=RiskMetrics.var(r, 0.05),
            cvar_95=RiskMetrics.cvar(r, 0.05),
        )
        if market_returns is not None:
            mr = np.asarray(market_returns, dtype=float).ravel()
            report.beta = RiskMetrics.beta(r, mr)
        if weights is not None:
            report.concentration = RiskMetrics.concentration(weights)
            conc = report.concentration
            if conc.get("hhi", 0) > 0.25:
                report.warnings.append(f"High concentration HHI={conc['hhi']:.2f}")
            if conc.get("top1", 0) > 0.30:
                report.warnings.append(f"Single position {conc['top1']:.0%} exceeds 30%")
        if factor_loadings:
            report.factor_exposure = factor_loadings
        if report.max_drawdown < -0.20:
            report.warnings.append(f"Max drawdown {report.max_drawdown:.1%} exceeds 20%")
        if report.var_95 < -0.05:
            report.warnings.append(f"VaR 95% {report.var_95:.1%} indicates significant tail risk")
        return report

    def rolling_correlation(self, returns_df: pd.DataFrame, window: int = 60) -> pd.DataFrame:
        """Rolling correlation warning: diversification failure when correlations spike."""
        # returns_df: columns tickers, rows dates
        # Return latest rolling correlation matrix
        if len(returns_df) < window:
            return returns_df.corr()
        return returns_df.iloc[-window:].corr()
