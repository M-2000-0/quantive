"""Live Market Data Connectors — Zero API Keys Required.

Free data sources:
- US Treasury (Fiscal Data API + treasury.gov CSV) — official par yield curves, daily
- ECB Statistical Data Warehouse — EUR reference rates, yield curves
- IMF IFS/WEO — macro/inflation/GDP/debt data
- World Bank Open Data — development indicators, GDP, debt stats
- NY Fed — SOFR, Treasury rates
- FRED — historical series for backtesting (requires API key)

Architecture:
  Provider → Adapter → Unified Schema (provider.py)
  Aggregation via MarketDataEngine (engine.py)
  Caching via TTL cache (cache.py)
  Quality via DataQualityService + DataQualityReport (quality.py, report.py)
"""
from app.market_data.provider import (
    MarketDataProvider,
    RateLimiter,
    Paginator,
    Page,
    YieldCurvePoint,
    YieldCurve,
    FxRate,
    MacroIndicator,
    EconomicSnapshot,
    BenchmarkRate,
    MaturityUnit,
    get_rate_limiter,
)
from app.market_data.cache import (
    MarketDataCache,
    get_cache,
    TTL_FX_RATES,
    TTL_YIELD_CURVE,
    TTL_INTEREST_RATES,
    TTL_ECONOMIC_INDICATORS,
    TTL_BOND_PRICES,
)
from app.market_data.quality import (
    DataQualityService,
    get_quality_service,
    HealthStatus,
    AnomalyType,
    SourceHealth,
    FreshnessInfo,
    ValidationRule,
    ValidationResult,
    Anomaly,
    INDICATOR_RANGES,
    VALIDATION_RULES,
)
from app.market_data.report import (
    DataQualityReport,
    QualityReport,
    ProviderReport,
    FreshnessReport,
    CoverageGap,
    format_report_text,
)
from app.market_data.engine import (
    MarketDataEngine,
    get_market_data_engine,
)
from app.market_data.treasury_fiscal import TreasuryProvider
from app.market_data.imf_connector import IMFProvider


