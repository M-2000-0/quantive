from quantive.investor.models import InvestorProfile, RiskTolerance, RiskCapacity, Horizon, InvestmentObjective
from quantive.investor.engine import InvestorEngine
from quantive.risk_engine.metrics import RiskMetrics
from quantive.risk_engine.engine import RiskEngine
import numpy as np
import pandas as pd

def test_risk_tolerance_vs_capacity_conflict():
    p = InvestorProfile(id="u1", risk_tolerance=RiskTolerance(max_acceptable_drawdown=0.40), risk_capacity=RiskCapacity(max_sustainable_drawdown=0.20), horizon=Horizon.LONG)
    assert p.risk_conflict() is not None
    eng = InvestorEngine()
    warns = eng.validate(p)
    assert any(c.code == "tolerance_exceeds_capacity" for c in warns)
    assert eng.effective_max_drawdown(p) == 0.20
    assert eng.effective_max_drawdown(p, require_ack=True) == 0.40

def test_no_conflict():
    p = InvestorProfile(id="u2", risk_tolerance=RiskTolerance(max_acceptable_drawdown=0.15), risk_capacity=RiskCapacity(max_sustainable_drawdown=0.20))
    assert p.risk_conflict() is None

def test_classification():
    eng = InvestorEngine()
    p = InvestorProfile(id="u3", risk_tolerance=RiskTolerance(max_acceptable_drawdown=0.05))
    assert eng.classify(p) == InvestmentObjective.CAPITAL_PRESERVATION
    p2 = InvestorProfile(id="u4", risk_tolerance=RiskTolerance(max_acceptable_drawdown=0.60))
    assert eng.classify(p2) == InvestmentObjective.SPECULATIVE

def test_horizon_mismatch():
    eng = InvestorEngine()
    p = InvestorProfile(id="u5", horizon=Horizon.SHORT, investment_objective=InvestmentObjective.SPECULATIVE, risk_tolerance=RiskTolerance(max_acceptable_drawdown=0.60))
    warns = eng.validate(p)
    assert any(c.code == "horizon_objective_mismatch" for c in warns)

def test_risk_metrics_vol_sharpe():
    rng = np.random.default_rng(0)
    rets = rng.normal(0.001, 0.02, 252)
    vol = RiskMetrics.volatility(rets)
    assert 0.1 < vol < 0.6
    sharpe = RiskMetrics.sharpe(rets, rf=0.02)
    assert isinstance(sharpe, float)
    dd = RiskMetrics.max_drawdown(np.cumprod(1+rets))
    assert dd <= 0

def test_risk_metrics_var_cvar():
    rets = np.array([-0.05, -0.03, -0.02, 0.01, 0.02, 0.03])
    var = RiskMetrics.var(rets, 0.05)
    cvar = RiskMetrics.cvar(rets, 0.05)
    assert cvar <= var

def test_concentration():
    c = RiskMetrics.concentration(np.array([0.5, 0.3, 0.2]))
    assert c["hhi"] == 0.38
    assert c["effective_n"] < 3

def test_risk_engine_report():
    rng = np.random.default_rng(1)
    rets = rng.normal(0.0005, 0.015, 252)
    eng = RiskEngine(risk_free_rate=0.02)
    report = eng.evaluate(rets, weights=np.array([0.4,0.3,0.2,0.1]))
    assert report.volatility > 0
    assert "hhi" in report.concentration
