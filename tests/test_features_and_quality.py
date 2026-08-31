import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from quantive.data.schema import OHLCVBar, bars_to_dataframe
from quantive.data.quality import DataQualityEngine
from quantive.features.store import Feature, FeatureStore, Normalization, MissingPolicy
from quantive.features.technical import TechnicalFeatures
from quantive.features.fundamental import FundamentalFeatures
from quantive.data.schema import FundamentalSnapshot
from datetime import date

def _make_df(n=60):
    rng = pd.date_range("2024-01-01", periods=n, freq="D")
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    close = np.maximum(close, 10)
    df = pd.DataFrame({
        "ticker": "AAPL",
        "timestamp": rng.tz_localize("UTC"),
        "open": close * (1 + np.random.randn(n)*0.002),
        "high": close * (1 + np.abs(np.random.randn(n)*0.005)),
        "low": close * (1 - np.abs(np.random.randn(n)*0.005)),
        "close": close,
        "volume": np.random.randint(1_000_000, 10_000_000, n).astype(float),
    })
    # enforce OHLC consistency
    df["high"] = df[["open","close","high"]].max(axis=1) * 1.001
    df["low"] = df[["open","close","low"]].min(axis=1) * 0.999
    return df

def test_ohlcv_bar_validation():
    bar = OHLCVBar(ticker="aapl", timestamp=datetime.now(timezone.utc), open=10, high=11, low=9, close=10.5, volume=1000)
    assert bar.ticker == "AAPL"

def test_bars_to_dataframe():
    bars = [OHLCVBar(ticker="AAPL", timestamp=datetime(2024,1,i+1, tzinfo=timezone.utc), open=10, high=11, low=9, close=10, volume=1000) for i in range(1,4)]
    df = bars_to_dataframe(bars)
    assert len(df) == 3

def test_quality_engine_passes_clean():
    df = _make_df(40)
    engine = DataQualityEngine()
    report = engine.check(df, dataset_id="test")
    assert report.passed, report.issues

def test_quality_engine_flags_duplicates():
    df = _make_df(10)
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    engine = DataQualityEngine()
    report = engine.check(df)
    assert any(i.code == "duplicate_records" for i in report.issues)

def test_quality_engine_flags_missing():
    df = _make_df(10)
    df.loc[0, "close"] = np.nan
    engine = DataQualityEngine()
    report = engine.check(df)
    assert any(i.code == "missing_values" for i in report.issues)
    assert not report.passed

def test_technical_sma_rsi():
    df = _make_df(50)
    sma = TechnicalFeatures.sma(df, 20)
    assert sma.notna().sum() > 0
    rsi = TechnicalFeatures.rsi(df, 14)
    assert rsi.dropna().between(0,100).all()

def test_technical_bollinger():
    df = _make_df(40)
    bb = TechnicalFeatures.bollinger(df, 20)
    assert "bb_upper" in bb.columns
    assert len(bb) == len(df)

def test_feature_store_register_compute():
    df = _make_df(40)
    store = FeatureStore()
    store.register(Feature(name="sma_20", source="technical", calculation_method="SMA 20", lookback_period=20, normalization=Normalization.NONE), computor=lambda d: TechnicalFeatures.sma(d,20))
    store.register(Feature(name="rsi_14", source="technical", calculation_method="RSI 14", lookback_period=14, normalization=Normalization.ZSCORE, missing_value_policy=MissingPolicy.FORWARD_FILL), computor=lambda d: TechnicalFeatures.rsi(d,14))
    out = store.compute(df, ["sma_20","rsi_14"])
    assert "sma_20" in out.columns and "rsi_14" in out.columns
    # z-scored rsi should have ~0 mean
    assert abs(out["rsi_14"].mean()) < 0.5

def test_fundamental_scores():
    snap = FundamentalSnapshot(ticker="AAPL", as_of=date(2024,12,31), pe=22, forward_pe=20, roe=0.25, debt_to_equity=0.5, interest_coverage=8, current_ratio=1.8, revenue_growth=0.08, accruals=0.02)
    scored = FundamentalFeatures.score(snap)
    assert "overall_score" in scored
    assert 0 <= scored["overall_score"] <= 100
    assert scored["quality"]["flags"] == []

def test_fundamental_flags_high_accruals():
    snap = FundamentalSnapshot(ticker="XYZ", as_of=date(2024,12,31), accruals=0.25)
    q = FundamentalFeatures.earnings_quality(snap)
    assert "high_accruals" in q["flags"]
