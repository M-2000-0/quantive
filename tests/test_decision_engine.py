import numpy as np
import pandas as pd
from quantive.decision.engine import DecisionEngine
from quantive.investor.models import InvestorProfile, RiskTolerance, RiskCapacity
from datetime import date
from quantive.data.schema import FundamentalSnapshot

def test_rank_and_portfolio():
    eng = DecisionEngine()
    tickers = ["AAPL","MSFT","GOOG"]
    exp = {"AAPL":0.08,"MSFT":0.06,"GOOG":0.10}
    conf = {"AAPL":0.7,"MSFT":0.6,"GOOG":0.5}
    risks = {"AAPL":0.15,"MSFT":0.12,"GOOG":0.20}
    snaps = {
        "AAPL": FundamentalSnapshot(ticker="AAPL", as_of=date(2024,12,31), pe=20, roe=0.25, debt_to_equity=0.3, revenue_growth=0.08),
        "MSFT": FundamentalSnapshot(ticker="MSFT", as_of=date(2024,12,31), pe=28, roe=0.20, debt_to_equity=0.4, revenue_growth=0.06),
        "GOOG": FundamentalSnapshot(ticker="GOOG", as_of=date(2024,12,31), pe=22, roe=0.18, debt_to_equity=0.2, revenue_growth=0.12),
    }
    rankings = eng.rank_stocks(tickers, exp, conf, risks, fundamental_snapshots=snaps)
    assert len(rankings)==3
    assert rankings[0].quantive_score >= rankings[-1].quantive_score
    # §68 shape
    d = rankings[0].to_dict()
    for key in ["ticker","quantive_score","expected_return","confidence","risk","momentum_score","fundamental_score","sentiment_score","regime_score","diversification_score","quantum_optimization_score","key_risks","key_reasons"]:
        assert key in d

    cov = np.eye(3)*0.04
    investor = InvestorProfile(id="u1", risk_tolerance=RiskTolerance(max_acceptable_drawdown=0.25), risk_capacity=RiskCapacity(max_sustainable_drawdown=0.25), max_position_size=0.5)
    port = eng.recommend_portfolio(rankings, cov, investor, method="max_sharpe", top_n=3)
    # §69 shape
    assert "portfolio" in port and len(port["portfolio"])==3
    assert abs(sum(p["allocation"] for p in port["portfolio"])-1) < 1e-6
    for key in ["expected_return","expected_volatility","max_drawdown_estimate","sharpe_estimate","diversification_score","confidence","optimization_method","model_version"]:
        assert key in port
