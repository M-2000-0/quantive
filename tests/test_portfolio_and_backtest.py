import numpy as np
import pandas as pd
from quantive.portfolio.optimizer import PortfolioOptimizer, Constraints
from quantive.backtesting.engine import BacktestEngine, TransactionCostModel

def _rand_cov(n=5, seed=0):
    rng = np.random.default_rng(seed)
    A = rng.normal(size=(n,n))
    cov = A @ A.T / 10 + np.eye(n)*0.01
    return cov

def test_equal_weight():
    opt = PortfolioOptimizer()
    w = opt.equal_weight(4)
    assert abs(w.sum()-1) < 1e-9
    assert all(w == 0.25)

def test_mean_variance_bounds():
    cov = _rand_cov(4)
    mu = np.array([0.08, 0.06, 0.10, 0.04])
    opt = PortfolioOptimizer(Constraints(max_position=0.5))
    w = opt.mean_variance(mu, cov, risk_aversion=2.0)
    assert abs(w.sum()-1) < 1e-6
    assert (w <= 0.5+1e-6).all()
    assert (w >= -1e-9).all()

def test_risk_parity():
    cov = _rand_cov(3)
    w = PortfolioOptimizer().risk_parity(cov)
    assert abs(w.sum()-1) < 1e-6

def test_max_div():
    cov = _rand_cov(3)
    w = PortfolioOptimizer().max_diversification(cov)
    assert abs(w.sum()-1) < 1e-6

def test_hrp():
    cov = _rand_cov(4)
    w = PortfolioOptimizer().hrp(cov)
    assert abs(w.sum()-1) < 1e-6

def test_black_litterman():
    cov = _rand_cov(3)
    caps = np.array([1e9, 2e9, 1.5e9])
    w = PortfolioOptimizer().black_litterman(caps, cov)
    assert abs(w.sum()-1) < 1e-6

def test_backtest_walk_forward():
    # synthetic prices
    dates = pd.date_range("2020-01-01", periods=400, freq="B")
    rng = np.random.default_rng(0)
    prices = pd.DataFrame({f"STK{i}": 100*np.cumprod(1+rng.normal(0.0005, 0.02, 400)) for i in range(3)}, index=dates)
    def equal_signal(train):
        return pd.Series(1/3, index=train.columns)
    eng = BacktestEngine(TransactionCostModel(commission_bps=5, spread_bps=5, slippage_bps=1))
    res = eng.walk_forward(prices, equal_signal, train_window=60, test_window=20)
    assert len(res.returns) > 0
    assert "sharpe" in res.scorecard
    assert "cagr" in res.scorecard
    assert res.scorecard["n_periods"] == len(res.returns)

def test_backtest_transaction_costs_reduce_return():
    dates = pd.date_range("2020-01-01", periods=200, freq="B")
    rng = np.random.default_rng(1)
    prices = pd.DataFrame({"A": 100*np.cumprod(1+rng.normal(0.001,0.01,200)), "B": 100*np.cumprod(1+rng.normal(0.001,0.01,200))}, index=dates)
    def momentum_signal(train):
        rets = train.pct_change().mean()
        # pick winner
        w = pd.Series(0, index=train.columns, dtype=float)
        w[rets.idxmax()] = 1.0
        return w
    eng_low = BacktestEngine(TransactionCostModel(commission_bps=0, spread_bps=0, slippage_bps=0))
    eng_high = BacktestEngine(TransactionCostModel(commission_bps=100, spread_bps=100, slippage_bps=50))
    r_low = eng_low.walk_forward(prices, momentum_signal, train_window=40, test_window=20)
    r_high = eng_high.walk_forward(prices, momentum_signal, train_window=40, test_window=20)
    # high costs should not improve net return vs low costs (allow equality due to no turnover)
    assert r_high.returns.mean() <= r_low.returns.mean() + 1e-9
