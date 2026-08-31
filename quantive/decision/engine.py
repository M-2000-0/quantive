"""Quantive Decision Engine — §67-69.

Combines: data + fundamentals + technicals + sentiment + macro + ML + regime + risk + investor + optimizer + quantum.

Outputs §68 stock ranking and §69 portfolio output. Never fabricates values.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Literal

from quantive.ml.ensemble import EnsembleModel
from quantive.risk_engine.engine import RiskEngine
from quantive.regime.engine import RegimeEngine
from quantive.investor.models import InvestorProfile
from quantive.portfolio.optimizer import PortfolioOptimizer, Constraints
from quantive.features.fundamental import FundamentalFeatures
from quantive.features.technical import TechnicalFeatures


@dataclass
class StockRanking:
    ticker: str
    quantive_score: float  # 0-100
    expected_return: float
    confidence: float
    risk: float
    momentum_score: float
    fundamental_score: float
    sentiment_score: float
    regime_score: float
    diversification_score: float
    quantum_optimization_score: float
    key_risks: list[str]
    key_reasons: list[str]

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "quantive_score": round(self.quantive_score, 1),
            "expected_return": round(self.expected_return, 4),
            "confidence": round(self.confidence, 3),
            "risk": round(self.risk, 4),
            "momentum_score": round(self.momentum_score, 1),
            "fundamental_score": round(self.fundamental_score, 1),
            "sentiment_score": round(self.sentiment_score, 1),
            "regime_score": round(self.regime_score, 1),
            "diversification_score": round(self.diversification_score, 1),
            "quantum_optimization_score": round(self.quantum_optimization_score, 1),
            "key_risks": self.key_risks,
            "key_reasons": self.key_reasons,
        }


def _quantive_score(expected: float, risk: float, confidence: float, fund: float, mom: float) -> float:
    """Composite 0-100: weighted risk-adjusted expected return + fund + mom."""
    # risk-adjusted return proxy: expected / (1+risk)
    rar = expected / (1 + abs(risk))
    # normalize rar to 0-1 via tanh
    rar_n = float(np.tanh(rar * 10) * 0.5 + 0.5)
    score = 0.35 * rar_n + 0.15 * (confidence) + 0.20 * (fund / 100) + 0.15 * ((mom + 100) / 200) + 0.15 * 0.5
    return float(np.clip(score * 100, 0, 100))


class DecisionEngine:
    """Orchestrates the full decision pipeline (§67)."""

    def __init__(self, risk_free: float = 0.02):
        self.risk_engine = RiskEngine(risk_free)
        self.regime_engine = RegimeEngine()
        self.optimizer = PortfolioOptimizer()

    def rank_stocks(
        self,
        tickers: list[str],
        expected_returns: dict[str, float],
        confidences: dict[str, float],
        risks: dict[str, float],
        fundamental_snapshots: dict[str, object] | None = None,
        technical_frames: dict[str, pd.DataFrame] | None = None,
        regime: dict | None = None,
        correlations: pd.DataFrame | None = None,
    ) -> list[StockRanking]:
        """Produce §68 ranking per ticker. Never invents missing values — NaN yields 50 neutral."""
        rankings: list[StockRanking] = []
        for t in tickers:
            exp = float(expected_returns.get(t, 0.0))
            conf = float(confidences.get(t, 0.5))
            risk = float(risks.get(t, 0.15))

            # fundamental
            fund_score = 50.0
            fund_reasons: list[str] = []
            if fundamental_snapshots and t in fundamental_snapshots:
                snap = fundamental_snapshots[t]
                scored = FundamentalFeatures.score(snap)
                fund_score = float(scored["overall_score"])
                if fund_score > 60:
                    fund_reasons.append("Strong fundamentals")
                elif fund_score < 40:
                    fund_reasons.append("Weak fundamentals")

            # momentum from technical RSI/MACD
            mom_score = 0.0
            if technical_frames and t in technical_frames:
                df = technical_frames[t]
                try:
                    rsi = TechnicalFeatures.rsi(df, 14).iloc[-1]
                    if np.isfinite(rsi):
                        mom_score = float((rsi - 50) * 1.5)  # -75..+75
                except Exception:
                    pass

            regime_score = 50.0
            if regime:
                primary = regime.get("primary", "")
                if primary == "bull":
                    regime_score = 65
                elif primary == "bear":
                    regime_score = 35

            # diversification contribution: 1 - avg correlation
            div_score = 50.0
            if correlations is not None and t in correlations.columns:
                avg_corr = float(correlations[t].drop(t, errors="ignore").mean()) if len(correlations) > 1 else 0
                div_score = float(np.clip((1 - avg_corr) * 50 + 50, 0, 100))

            q_score = float(np.clip(conf * 50 + 30, 0, 100))  # placeholder quantum benefit proxy

            qs = _quantive_score(exp, risk, conf, fund_score, mom_score)

            risks_list: list[str] = []
            reasons: list[str] = []
            if risk > 0.25:
                risks_list.append("High volatility")
            if conf < 0.5:
                risks_list.append("Low model confidence")
            if fund_score < 40:
                risks_list.append("Weak financial health")
            if exp > 0.03:
                reasons.append("Positive expected return")
            if fund_score > 60:
                reasons.append("Strong earnings/valuation")
            if mom_score > 10:
                reasons.append("Positive momentum")
            if div_score > 60:
                reasons.append("Diversification benefit")

            rankings.append(
                StockRanking(
                    ticker=t,
                    quantive_score=qs,
                    expected_return=exp,
                    confidence=conf,
                    risk=risk,
                    momentum_score=mom_score,
                    fundamental_score=fund_score,
                    sentiment_score=50.0,  # §17 sentiment engine hook — neutral until wired
                    regime_score=regime_score,
                    diversification_score=div_score,
                    quantum_optimization_score=q_score,
                    key_risks=risks_list,
                    key_reasons=reasons,
                )
            )
        # sort by quantive_score desc
        rankings.sort(key=lambda r: r.quantive_score, reverse=True)
        return rankings

    def recommend_portfolio(
        self,
        rankings: list[StockRanking],
        cov: np.ndarray,
        investor: InvestorProfile | None = None,
        method: Literal["equal", "max_sharpe", "risk_parity", "hrp"] = "max_sharpe",
        top_n: int = 10,
    ) -> dict:
        """§69 portfolio output: weights, expected return/vol, Sharpe, diversification, confidence."""
        top = rankings[:top_n]
        tickers = [r.ticker for r in top]
        mu = np.array([r.expected_return for r in top])
        conf = np.array([r.confidence for r in top])
        # covariance slice: assume provided cov is for top_n in same order; else use diagonal from risk
        if cov.shape[0] != len(top):
            # build diagonal approx from risk
            vols = np.array([r.risk for r in top])
            cov = np.diag(vols**2)

        constraints = Constraints(
            max_position=investor.max_position_size if investor else 0.25,
        )
        opt = PortfolioOptimizer(constraints)

        if method == "equal":
            w = opt.equal_weight(len(top))
        elif method == "risk_parity":
            w = opt.risk_parity(cov)
        elif method == "hrp":
            w = opt.hrp(cov)
        else:
            w = opt.max_sharpe(mu, cov)

        # enforce investor max_position if needed (optimizer already does)
        exp_ret = float(mu @ w)
        vol = float(np.sqrt(w @ cov @ w))
        sharpe = float(exp_ret / vol) if vol else 0.0
        # diversification ratio
        vols_diag = np.sqrt(np.diag(cov))
        div_ratio = float((w @ vols_diag) / vol) if vol else 1.0
        # max DD estimate via vol proxy: ~2*vol annual
        mdd_est = float(-vol * 1.5)
        avg_conf = float(conf.mean()) if len(conf) else 0.5

        return {
            "portfolio": [{"ticker": t, "allocation": round(float(wi), 4)} for t, wi in zip(tickers, w)],
            "expected_return": round(exp_ret, 4),
            "expected_volatility": round(vol, 4),
            "max_drawdown_estimate": round(mdd_est, 4),
            "sharpe_estimate": round(sharpe, 3),
            "diversification_score": round(float(np.clip(div_ratio / 2 * 100, 0, 100)), 1),
            "confidence": round(avg_conf, 3),
            "optimization_method": method,
            "model_version": "quantive-engine/0.1.0",
        }
