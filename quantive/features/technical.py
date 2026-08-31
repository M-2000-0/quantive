"""Technical indicators — pure functions returning pd.Series.

All functions operate on a DataFrame with columns open/high/low/close/volume
and return a same-index Series. No single indicator is treated as a buy/sell
signal; they are features for ML / optimizer.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _close(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["close"], errors="coerce")


class TechnicalFeatures:
    """Namespace for technical indicator calculators."""

    # -- Trend --------------------------------------------------------------
    @staticmethod
    def sma(df: pd.DataFrame, window: int = 20) -> pd.Series:
        return _close(df).rolling(window, min_periods=window).mean()

    @staticmethod
    def ema(df: pd.DataFrame, window: int = 20) -> pd.Series:
        return _close(df).ewm(span=window, adjust=False, min_periods=window).mean()

    @staticmethod
    def macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        c = _close(df)
        fast_ema = c.ewm(span=fast, adjust=False).mean()
        slow_ema = c.ewm(span=slow, adjust=False).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        hist = macd_line - signal_line
        return pd.DataFrame({"macd": macd_line, "macd_signal": signal_line, "macd_hist": hist}, index=df.index)

    @staticmethod
    def adx(df: pd.DataFrame, window: int = 14) -> pd.Series:
        high = pd.to_numeric(df["high"], errors="coerce")
        low = pd.to_numeric(df["low"], errors="coerce")
        close = _close(df)
        plus_dm = high.diff()
        minus_dm = low.diff() * -1
        plus_dm = pd.Series(np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0.0), index=df.index)
        minus_dm = pd.Series(np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0.0), index=df.index)
        tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(window).mean()
        plus_di = 100 * (plus_dm.rolling(window).mean() / atr.replace(0, np.nan))
        minus_di = 100 * (minus_dm.rolling(window).mean() / atr.replace(0, np.nan))
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        return dx.rolling(window).mean()

    # -- Momentum -----------------------------------------------------------
    @staticmethod
    def rsi(df: pd.DataFrame, window: int = 14) -> pd.Series:
        c = _close(df)
        delta = c.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
        avg_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def stochastic(df: pd.DataFrame, k_window: int = 14, d_window: int = 3) -> pd.DataFrame:
        high = pd.to_numeric(df["high"], errors="coerce")
        low = pd.to_numeric(df["low"], errors="coerce")
        c = _close(df)
        lowest = low.rolling(k_window).min()
        highest = high.rolling(k_window).max()
        k = 100 * (c - lowest) / (highest - lowest).replace(0, np.nan)
        d = k.rolling(d_window).mean()
        return pd.DataFrame({"stoch_k": k, "stoch_d": d}, index=df.index)

    @staticmethod
    def roc(df: pd.DataFrame, window: int = 12) -> pd.Series:
        c = _close(df)
        return 100 * (c / c.shift(window) - 1)

    @staticmethod
    def momentum(df: pd.DataFrame, window: int = 10) -> pd.Series:
        return _close(df).diff(window)

    # -- Volatility ---------------------------------------------------------
    @staticmethod
    def atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
        high = pd.to_numeric(df["high"], errors="coerce")
        low = pd.to_numeric(df["low"], errors="coerce")
        c = _close(df)
        tr = pd.concat([high - low, (high - c.shift()).abs(), (low - c.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(window).mean()

    @staticmethod
    def bollinger(df: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
        c = _close(df)
        sma = c.rolling(window).mean()
        std = c.rolling(window).std()
        return pd.DataFrame({
            "bb_mid": sma,
            "bb_upper": sma + num_std * std,
            "bb_lower": sma - num_std * std,
            "bb_width": (2 * num_std * std) / sma.replace(0, np.nan),
            "bb_pct": (c - (sma - num_std * std)) / (2 * num_std * std).replace(0, np.nan),
        }, index=df.index)

    @staticmethod
    def realized_volatility(df: pd.DataFrame, window: int = 20) -> pd.Series:
        ret = np.log(_close(df) / _close(df).shift(1))
        return ret.rolling(window).std() * np.sqrt(252)

    # -- Volume -------------------------------------------------------------
    @staticmethod
    def obv(df: pd.DataFrame) -> pd.Series:
        c = _close(df)
        vol = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
        direction = np.sign(c.diff()).fillna(0)
        return (direction * vol).cumsum()

    @staticmethod
    def vwap(df: pd.DataFrame, window: int = 20) -> pd.Series:
        high = pd.to_numeric(df["high"], errors="coerce")
        low = pd.to_numeric(df["low"], errors="coerce")
        c = _close(df)
        vol = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
        tp = (high + low + c) / 3
        return (tp * vol).rolling(window).sum() / vol.rolling(window).sum().replace(0, np.nan)

    @staticmethod
    def relative_volume(df: pd.DataFrame, window: int = 20) -> pd.Series:
        vol = pd.to_numeric(df["volume"], errors="coerce")
        return vol / vol.rolling(window).mean().replace(0, np.nan)

    # -- Price structure ----------------------------------------------------
    @staticmethod
    def support_resistance(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        high = pd.to_numeric(df["high"], errors="coerce")
        low = pd.to_numeric(df["low"], errors="coerce")
        return pd.DataFrame({
            "resistance": high.rolling(window).max(),
            "support": low.rolling(window).min(),
        }, index=df.index)

    @staticmethod
    def higher_highs_lower_lows(df: pd.DataFrame) -> pd.Series:
        """+1 higher-highs, -1 lower-lows, 0 otherwise (last window extremum comparison)."""
        c = _close(df)
        hh = (c > c.shift(1)) & (c.shift(1) > c.shift(2))
        ll = (c < c.shift(1)) & (c.shift(1) < c.shift(2))
        return pd.Series(np.where(hh, 1, np.where(ll, -1, 0)), index=df.index, dtype=float)
