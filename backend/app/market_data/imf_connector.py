"""IMF IFS / WEO connector.

Uses the IMF Data API (imf.org/external/datamapi):
- International Financial Statistics (IFS): inflation, interest rates, FX
- World Economic Outlook (WEO): GDP, debt-to-GDP, fiscal balances

Free, no API key required. Uses IMF's JSON REST API.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Any

from app.market_data.provider import (
    MarketDataProvider, YieldCurve, FxRate, MacroIndicator,
    EconomicSnapshot, BenchmarkRate, get_rate_limiter,
)
from app.market_data.cache import TTL_ECONOMIC_INDICATORS, TTL_INTEREST_RATES, get_cache

logger = logging.getLogger("quantive.market_data.imf")

IMF_BASE = "https://www.imf.org/external/datamapi"

# IMF IFS indicator codes relevant to sovereign debt
IFS_INDICATORS = {
    "inflation_cpi": "PCPI_IX",       # Consumer Price Index
    "inflation_pmi": "PCPIE_IX",      # Producer Price Index
    "interest_rate": "LP_RATE",       # Lending Rate
    "fx_rate_usd_local": "PXOX_R",    # Exchange rate (local currency per USD)
    "current_account": "BCA_NGDPD",   # Current account balance (% GDP)
    "fiscal_balance": "GGR_G01_GDP",  # General gov revenue (% GDP)
}

# WEO indicators
WEO_INDICATORS = {
    "gdp_nominal": "NGDPD",           # Nominal GDP (USD)
    "gdp_growth": "NGDP_RPCH",        # Real GDP growth (%)
    "debt_to_gdp": "GGXWDG_NGDP",     # General gov gross debt (% GDP)
    "fiscal_balance": "GGXCNL_NGDP",  # General gov net lending (% GDP)
    "inflation": "PCPIE_IX",          # Inflation, average
    "unemployment": "LRHUTTTT",       # Unemployment rate
}

# ISO2 → ISO3 mapping (World Bank uses ISO2, IMF uses ISO3 in some endpoints)
ISO2_TO_ISO3 = {
    "US": "USA", "GB": "GBR", "DE": "DEU", "FR": "FRA",
    "JP": "JPN", "CN": "CHN", "IN": "IND", "BR": "BRA",
    "NG": "NGA", "GH": "GHA", "KE": "KEN", "ZA": "ZAF",
    "EG": "EGY", "MX": "MEX", "AR": "ARG", "CO": "COL",
    "AU": "AUS", "CA": "CAN", "KR": "KOR", "SG": "SGP",
}


class IMFProvider(MarketDataProvider):
    """IMF IFS + WEO connector.

    Free, no API key required.
    """

    @property
    def name(self) -> str:
        return "IMF (IFS/WEO)"

    @property
    def is_available(self) -> bool:
        return True

    def _iso3(self, country_code: str) -> str:
        return ISO2_TO_ISO3.get(country_code.upper(), country_code.upper())

    def get_yield_curve(self, country_code: str = "US", date: Optional[str] = None) -> Optional[YieldCurve]:
        """IMF does not publish real-time yield curves — return None."""
        return None

    def get_fx_rate(self, pair: str, date: Optional[str] = None) -> Optional[FxRate]:
        """Fetch IMF IFS exchange rate (periodic, not real-time)."""
        parts = pair.upper().replace("/", "")
        if len(parts) != 6:
            return None
        # IMF publishes rates as local currency per USD (for most currencies)
        # For EUR/USD: IMF publishes USD per EUR
        base, quote = parts[:3], parts[3:]
        # Use IMF IFS: rate is typically in domestic currency per USD
        indicator_map = {
            "USD": "PXOX_R",  # USD per ... (needs target currency)
            "EUR": "EUR",
        }
        # IMF IFS endpoint: /IFS?area={country}&indicator={indicator}
        country = self._iso3(base)
        indicator = "PXOX_R"  # placeholder; IMF publishes a broad set
        url = f"{IMF_BASE}/IFS"
        params = {
            "area": country,
            "indicator": indicator,
            "startPeriod": (datetime.now().year - 1),
            "endPeriod": datetime.now().year,
            "format": "json",
        }
        data = self._request("GET", url, params=params, source="imf_ifs")
        if not data:
            return None

        # Parse IMF IFS response structure
        try:
            values = data.get("value", [])
            if not values:
                return None
            latest = max(values, key=lambda v: v.get("period", ""))
            rate = latest.get("value")
            if rate is None:
                return None
            return FxRate(
                pair=pair,
                rate=float(rate),
                date=latest.get("period", ""),
                source="IMF IFS",
            )
        except (TypeError, ValueError, KeyError):
            return None

    def get_fx_rates(self, base: str = "USD") -> list:
        """Fetch all key IMF FX rates."""
        rates = []
        pairs = ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "USD/CNY", "USD/MXN", "USD/BRL"]
        for pair in pairs:
            rate = self.get_fx_rate(pair)
            if rate:
                rates.append(rate)
        return rates

    def get_benchmark_rates(self) -> list[BenchmarkRate]:
        """Fetch IMF IFS lending/policy rates."""
        cache = get_cache()
        cache_key = "imf_benchmark_rates"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        rates: list[BenchmarkRate] = []
        country = self._iso3("US")
        # IMF IFS: lending rate for US
        url = f"{IMF_BASE}/IFS"
        params = {
            "area": country,
            "indicator": "LP_RATE",
            "startPeriod": datetime.now().year - 1,
            "endPeriod": datetime.now().year,
            "format": "json",
        }
        data = self._request("GET", url, params=params, source="imf_ifs")
        if data:
            try:
                values = data.get("value", [])
                for v in sorted(values, key=lambda x: x.get("period", ""), reverse=True)[:3]:
                    rate_val = v.get("value")
                    if rate_val is not None:
                        rates.append(BenchmarkRate(
                            name="IMF Lending Rate (US)",
                            rate_pct=float(rate_val),
                            date=v.get("period", ""),
                            source="IMF IFS",
                        ))
            except (TypeError, ValueError):
                pass

        cache.set(cache_key, rates, TTL_INTEREST_RATES)
        return rates

    def get_economic_snapshot(
        self, country_code: str, indicators: Optional[list[str]] = None,
    ) -> Optional[EconomicSnapshot]:
        """Fetch a macro snapshot from IMF WEO + IFS."""
        iso3 = self._iso3(country_code)
        indicator_list = indicators or list(WEO_INDICATORS.keys())
        wb_indicators = [WEO_INDICATORS.get(ind, ind) for ind in indicator_list]

        all_indicators: list[MacroIndicator] = []

        # Fetch WEO indicators
        for ind_name, ind_code in WEO_INDICATORS.items():
            if indicators and ind_name not in indicators:
                continue
            data = self._request(
                "GET", f"{IMF_BASE}/WEO",
                params={
                    "country": iso3,
                    "indicator": ind_code,
                    "format": "json",
                },
                source="imf_weo",
            )
            if not data:
                continue
            try:
                for item in data.get("value", []):
                    val = item.get("value")
                    if val is not None:
                        all_indicators.append(MacroIndicator(
                            indicator=ind_name,
                            value=float(val),
                            unit="%",
                            country=country_code,
                            date=str(item.get("year", "")),
                            source="IMF WEO",
                            indicator_code=ind_code,
                        ))
            except (TypeError, ValueError):
                continue

        # Fetch IFS indicators (inflation, rates)
        for ind_name, ind_code in IFS_INDICATORS.items():
            if indicators and ind_name not in indicators:
                continue
            data = self._request(
                "GET", f"{IMF_BASE}/IFS",
                params={
                    "area": iso3,
                    "indicator": ind_code,
                    "startPeriod": datetime.now().year - 2,
                    "endPeriod": datetime.now().year,
                    "format": "json",
                },
                source="imf_ifs",
            )
            if not data:
                continue
            try:
                values = data.get("value", [])
                for v in values:
                    val = v.get("value")
                    if val is not None:
                        all_indicators.append(MacroIndicator(
                            indicator=ind_name,
                            value=float(val),
                            unit="%",
                            country=country_code,
                            date=str(v.get("period", "")),
                            source="IMF IFS",
                            indicator_code=ind_code,
                        ))
            except (TypeError, ValueError):
                continue

        if not all_indicators:
            return None

        return EconomicSnapshot(
            country_code=country_code,
            country_name=iso3,
            indicators=all_indicators,
            source="IMF (IFS/WEO)",
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        )

    def get_historical_series(self, series_id: str, start: str, end: str) -> list[dict]:
        """Fetch a historical time series from IMF IFS.

        ``series_id`` maps to an IMF indicator code.
        """
        country = self._iso3("US")
        url = f"{IMF_BASE}/IFS"
        params = {
            "area": country,
            "indicator": series_id,
            "startPeriod": start,
            "endPeriod": end,
            "format": "json",
        }
        data = self._request("GET", url, params=params, source="imf_ifs")
        if not data:
            return []

        series = []
        try:
            for item in data.get("value", []):
                series.append({
                    "date": item.get("period", ""),
                    "value": item.get("value"),
                    "indicator": series_id,
                    "source": "IMF IFS",
                })
        except TypeError:
            pass
        return series

    def get_inflation(self, country_code: str) -> list[dict]:
        """Fetch CPI/inflation data from IMF IFS."""
        return self.get_historical_series(
            "PCPI_IX",
            str(datetime.now().year - 5),
            str(datetime.now().year),
        )

    def get_gdp(self, country_code: str) -> list[dict]:
        """Fetch GDP data from IMF WEO."""
        iso3 = self._iso3(country_code)
        url = f"{IMF_BASE}/WEO"
        params = {
            "country": iso3,
            "indicator": "NGDPD,NGDP_RPCH,GGXWDG_NGDP",
            "format": "json",
        }
        data = self._request("GET", url, params=params, source="imf_weo")
        if not data:
            return []

        results = []
        try:
            for item in data.get("value", []):
                results.append({
                    "year": item.get("year"),
                    "nominal_gdp_usd": item.get("NGDPD"),
                    "gdp_growth_pct": item.get("NGDP_RPCH"),
                    "debt_to_gdp_pct": item.get("GGXWDG_NGDP"),
                    "source": "IMF WEO",
                })
        except TypeError:
            pass
        return results
