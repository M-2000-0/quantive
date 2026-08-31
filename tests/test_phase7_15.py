import numpy as np
import pandas as pd
from quantive.regime.engine import RegimeEngine
from quantive.quantum.backend import ClassicalSimulatorBackend, QuantumInspiredBackend, get_quantum_backend, QuantumProblem
from quantive.ml.models import RidgeModel, LassoModel, TreeModel
from quantive.ml.ensemble import EnsembleModel
from quantive.broker.base import PaperBroker, OrderSide
from quantive.execution.engine import ExecutionEngine, ExecutionConfig
from quantive.alerts.engine import AlertEngine

def test_regime_classifier():
    rng = np.random.default_rng(0)
    rets = pd.Series(rng.normal(0.001, 0.01, 200))
    eng = RegimeEngine()
    out = eng.classify(rets)
    assert "primary" in out and "scores" in out
    adapted = eng.adapt_weights({"momentum":0.5, "low_vol":0.5}, out)
    assert abs(sum(adapted.values())-1) < 1e-9

def test_quantum_backends():
    cov = np.eye(3)*0.04
    mu = np.array([0.08, 0.06, 0.10])
    prob = QuantumProblem(expected_returns=mu, cov=cov)
    for name in ["classical", "quantum_inspired"]:
        be = get_quantum_backend(name)
        res = be.optimize(prob)
        assert abs(res.weights.sum()-1) < 1e-6
        assert res.feasible
        assert res.backend in ("classical_cpu","simulator")

def test_ml_ensemble():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(100,5))
    y = X[:,0]*2 + X[:,1]*-1 + rng.normal(0,0.5,100)
    X_train, X_val = X[:70], X[70:]
    y_train, y_val = y[:70], y[70:]
    m1 = RidgeModel(alpha=1.0); m1.fit(X_train, y_train)
    m2 = LassoModel(alpha=0.1); m2.fit(X_train, y_train)
    m3 = TreeModel(n_estimators=20); m3.fit(X_train, y_train)
    ens = EnsembleModel([m1,m2,m3])
    ens.fit_weights(X_val, y_val)
    preds = ens.predict_with_uncertainty(X_val[:5])
    assert len(preds)==5
    assert all(0<=p.confidence<=1 for p in preds)
    assert preds[0].lower < preds[0].expected_return < preds[0].upper
    lb = ens.leaderboard
    assert len(lb)==3

def test_paper_broker():
    b = PaperBroker(10000)
    b.set_market_price("AAPL", 100)
    b.set_market_price("MSFT", 200)
    acc = b.get_account()
    assert acc.cash==10000
    o = b.place_order("AAPL", OrderSide.BUY, 10)
    assert o.status=="filled"
    assert len(b.get_positions())==1
    # sell
    o2 = b.place_order("AAPL", OrderSide.SELL, 5)
    assert b.get_account().cash > 0

def test_execution_safety():
    b = PaperBroker(100000)
    b.set_market_price("AAPL", 100)
    b.set_market_price("MSFT", 200)
    eng = ExecutionEngine(b, ExecutionConfig(max_order_size=5000, max_position_size=0.6, stale_price_seconds=9999))
    plans = eng.plan({"AAPL":0.5,"MSFT":0.5}, {"AAPL":0.0,"MSFT":0.0}, {"AAPL":100,"MSFT":200}, 10000)
    assert len(plans)==2
    orders = eng.execute(plans)
    assert len(orders)==2
    # kill switch
    eng.halt()
    try:
        eng.execute(plans)
        assert False, "should have raised"
    except RuntimeError:
        pass
    eng.resume()
    # duplicate guard
    eng2 = ExecutionEngine(b, ExecutionConfig(duplicate_window_seconds=60, stale_price_seconds=9999))
    eng2.execute(plans[:1])
    try:
        eng2.execute(plans[:1])
        assert False
    except ValueError as e:
        assert "Duplicate" in str(e)

def test_alerts():
    eng = AlertEngine(concentration_threshold=0.25, confidence_floor=0.6)
    alerts = eng.evaluate(concentration_hhi=0.3, confidence=0.4, risk_current=0.15, risk_previous=0.10, regime_previous="bull", regime_current="bear", drift_pct=0.05)
    assert len(alerts) >= 4
    assert any(a.severity.value=="warning" for a in alerts)
