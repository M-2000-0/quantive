"""Market Monitoring Models — Track stocks, crypto, commodities, forex, bonds.

Provides:
- MarketAsset: Universal asset representation across all classes
- PriceHistory: OHLCV time series with source metadata
- MarketSignal: Technical indicator signals with strength scores
- InsightRecord: Daily insights with priority and action type
- UserAlert: User-configured alerts with conditions and thresholds
- AlertHistory: Log of triggered alerts for analytics
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, Text, JSON,
    ForeignKey, Index, Enum as SAEnum
)
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class AssetClass(enum.Enum):
    STOCK = "stock"
    CRYPTO = "crypto"
    COMMODITY = "commodity"
    FX = "fx"
    BOND = "bond"
    ETF = "etf"


class SignalType(enum.Enum):
    RSI_OVERSOLD = "rsi_oversold"
    RSI_OVERBOUGHT = "rsi_overbought"
    MACD_BULLISH = "macd_bullish"
    MACD_BEARISH = "macd_bearish"
    VOLUME_SURGE = "volume_surge"
    PRICE_BREAKOUT = "price_breakout"
    MOVING_AVG_CROSS = "moving_avg_cross"
    BOLLINGER_BREAK = "bollinger_break"
    EARNINGS_UPCOMING = "earnings_upcoming"
    SENTIMENT_SHIFT = "sentiment_shift"
    WHALE_MOVEMENT = "whale_movement"
    YIELD_CHANGE = "yield_change"


class AlertType(enum.Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PRICE_CHANGE_PCT = "price_change_pct"
    RSI_CROSS = "rsi_cross"
    MACD_CROSS = "macd_cross"
    VOLUME_SPIKE = "volume_spike"
    PORTFOLIO_DRIFT = "portfolio_drift"
    EARNINGS_WARNING = "earnings_warning"
    CORRELATION_BREAK = "correlation_break"
    CUSTOM = "custom"


class InsightType(enum.Enum):
    MARKET_PULSE = "market_pulse"
    TOP_MOVERS = "top_movers"
    EMERGING_OPPORTUNITY = "emerging_opportunity"
    RISK_WARNING = "risk_warning"
    EARNINGS_ALERT = "earnings_alert"
    SENTIMENT_SHIFT = "sentiment_shift"
    DEFI_YIELD = "defi_yield"
    MACRO_SIGNAL = "macro_signal"


class Priority(enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MarketAsset(Base):
    __tablename__ = "market_assets"

    id = Column(String(36), primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    asset_class = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50))
    sector = Column(String(100))
    currency = Column(String(10), default="USD")

    # Current state
    current_price = Column(Float, default=0)
    previous_close = Column(Float, default=0)
    day_change_pct = Column(Float, default=0)
    market_cap = Column(Float, default=0)
    volume_24h = Column(Float, default=0)
    avg_volume_20d = Column(Float, default=0)

    # 52-week / historical
    high_52w = Column(Float, default=0)
    low_52w = Column(Float, default=0)
    ath = Column(Float, default=0)  # all-time high
    atl = Column(Float, default=0)  # all-time low

    # Technical indicators (latest)
    rsi_14 = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    sma_20 = Column(Float)
    sma_50 = Column(Float)
    sma_200 = Column(Float)
    bollinger_upper = Column(Float)
    bollinger_lower = Column(Float)

    # Discovery scoring
    discovery_score = Column(Float, default=0)
    discovery_signals = Column(JSON, default=dict)
    is_rising_star = Column(Boolean, default=False)
    is_emerging = Column(Boolean, default=False)

    # Crypto-specific
    tvl = Column(Float)  # total value locked for DeFi
    wallet_growth_14d = Column(Float)  # % change
    active_wallets = Column(Integer)

    # Metadata
    data_quality_score = Column(Float, default=1.0)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_asset_class_symbol", "asset_class", "symbol", unique=True),
    )


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String(36), ForeignKey("market_assets.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    interval = Column(String(10), default="1d")  # 1m, 5m, 1h, 1d, 1w
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float, nullable=False)
    volume = Column(Float, default=0)
    source = Column(String(50))
    confidence = Column(Float, default=1.0)

    __table_args__ = (
        Index("idx_price_asset_time", "asset_id", "timestamp"),
    )


class MarketSignal(Base):
    __tablename__ = "market_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String(36), ForeignKey("market_assets.id"), nullable=False, index=True)
    signal_type = Column(String(30), nullable=False)
    direction = Column(String(10))  # bullish, bearish, neutral
    strength = Column(Float, default=0)  # 0-100
    indicator = Column(String(50))
    raw_value = Column(Float)
    threshold_breached = Column(Float)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    metadata_json = Column(JSON, default=dict)

    __table_args__ = (
        Index("idx_signal_asset_type", "asset_id", "signal_type"),
    )


class InsightRecord(Base):
    __tablename__ = "insight_records"

    id = Column(String(36), primary_key=True)
    insight_type = Column(String(30), nullable=False)
    title = Column(String(200), nullable=False)
    summary = Column(Text)
    details = Column(JSON, default=dict)
    assets_involved = Column(JSON, default=list)  # list of asset_ids
    priority = Column(String(10), default="medium")
    action_type = Column(String(20))  # buy, sell, hold, watch, rebalance
    confidence_score = Column(Float, default=0.5)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime)
    is_read = Column(Boolean, default=False)
    user_feedback = Column(String(10))  # up, down, null

    __table_args__ = (
        Index("idx_insight_type_priority", "insight_type", "priority"),
    )


class UserAlert(Base):
    __tablename__ = "user_alerts"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    asset_id = Column(String(36), ForeignKey("market_assets.id"), index=True)
    alert_type = Column(String(30), nullable=False)
    condition = Column(String(50))  # above, below, crosses, pct_change
    threshold = Column(Float)
    secondary_threshold = Column(Float)  # for range alerts
    is_active = Column(Boolean, default=True)
    delivery_channels = Column(JSON, default=["in_app"])  # in_app, email, sms, webhook
    repeat = Column(String(20), default="once")  # once, every_time, daily_summary
    triggered_at = Column(DateTime)
    acknowledged_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    metadata_json = Column(JSON, default=dict)

    __table_args__ = (
        Index("idx_alert_user_active", "user_id", "is_active"),
    )


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(36), ForeignKey("user_alerts.id"), nullable=False)
    user_id = Column(String(36), nullable=False, index=True)
    asset_symbol = Column(String(20))
    triggered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    trigger_value = Column(Float)
    threshold_value = Column(Float)
    delivery_status = Column(String(20), default="pending")  # sent, failed, pending
    acknowledged = Column(Boolean, default=False)
    metadata_json = Column(JSON, default=dict)
