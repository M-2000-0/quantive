"""
Smoke Tests — Automated verification of all critical endpoints.

Run: cd backend && python -m pytest tests/test_smoke.py -v
"""
import json
import urllib.request

BASE_URL = "http://127.0.0.1:8000"


def _get(path: str, timeout: int = 30) -> tuple[int, dict | str]:
    """Make a GET request and return (status_code, parsed_body)."""
    try:
        r = urllib.request.urlopen(f"{BASE_URL}{path}", timeout=timeout)
        ct = r.headers.get("Content-Type", "")
        body = r.read()
        if "json" in ct:
            return r.status, json.loads(body)
        return r.status, body.decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return 0, str(e)


def _post(path: str, data: dict, timeout: int = 30) -> tuple[int, dict | str]:
    """Make a POST request and return (status_code, parsed_body)."""
    try:
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            f"{BASE_URL}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        r = urllib.request.urlopen(req, timeout=timeout)
        ct = r.headers.get("Content-Type", "")
        resp = r.read()
        if "json" in ct:
            return r.status, json.loads(resp)
        return r.status, resp.decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return 0, str(e)


# ── Health & Readiness ───────────────────────────────────────────────

def test_liveness():
    status, body = _get("/api/health/live")
    assert status == 200, f"Liveness probe failed: {status}"
    assert body["status"] == "alive"


def test_readiness():
    status, body = _get("/api/health/ready")
    assert status == 200, f"Readiness probe failed: {status}"
    assert body["status"] == "ready"
    assert body["checks"]["database"] == "healthy"


def test_system_status():
    status, body = _get("/api/health/status")
    assert status == 200, f"System status failed: {status}"
    assert body["status"] == "operational"
    assert "uptime_hours" in body


# ── Core Pages ───────────────────────────────────────────────────────

def test_dashboard_page():
    status, _ = _get("/dashboard")
    assert status == 200, f"Dashboard page failed: {status}"


def test_trading_hub_page():
    status, _ = _get("/trading-hub")
    assert status == 200, f"Trading Hub page failed: {status}"


def test_trading_tools_page():
    status, _ = _get("/trading-tools")
    assert status == 200, f"Trading Tools page failed: {status}"


def test_external_factors_page():
    status, _ = _get("/external-factors")
    assert status == 200, f"External Factors page failed: {status}"


def test_landing_page():
    status, _ = _get("/landing")
    assert status == 200, f"Landing page failed: {status}"


def test_pricing_page():
    status, _ = _get("/pricing")
    assert status == 200, f"Pricing page failed: {status}"


# ── Trading Intelligence ─────────────────────────────────────────────

def test_market_overview():
    status, body = _get("/api/trading/market-overview")
    assert status == 200, f"Market overview failed: {status}"
    stocks = [s for s in body.get("top_stocks", []) if s.get("price", 0) > 0]
    assert len(stocks) > 0, "No stocks with real prices"


def test_top_movers():
    status, body = _get("/api/trading/top-movers", timeout=60)
    assert status == 200, f"Top movers failed: {status}"
    assert len(body.get("gainers", [])) > 0, "No gainers"


def test_sectors():
    status, body = _get("/api/trading/sectors")
    assert status == 200, f"Sectors failed: {status}"
    sectors = [s for s in body.get("sectors", []) if s.get("price", 0) > 0]
    assert len(sectors) > 0, "No sectors with real prices"


def test_etfs():
    status, body = _get("/api/trading/etf-overview")
    assert status == 200, f"ETFs failed: {status}"
    etfs = [e for e in body.get("etfs", []) if e.get("price", 0) > 0]
    assert len(etfs) > 0, "No ETFs with real prices"


def test_technical_analysis():
    status, body = _get("/api/trading/technical-analysis/NVDA")
    assert status == 200, f"Technical analysis failed: {status}"
    assert "signal" in body, "No signal in response"
    assert "technicals" in body, "No technicals in response"


def test_options_data():
    status, body = _get("/api/trading/options/NVDA")
    assert status == 200, f"Options data failed: {status}"
    assert "options_chain" in body, "No options chain"


def test_stock_search():
    status, body = _get("/api/trading/search?q=NVIDIA")
    assert status == 200, f"Stock search failed: {status}"
    assert body["count"] > 0, "No results"


# ── Trading Tools ────────────────────────────────────────────────────

def test_backtest_strategies():
    status, body = _get("/api/backtest/strategies")
    assert status == 200, f"Backtest strategies failed: {status}"
    assert len(body["strategies"]) == 4, "Expected 4 strategies"


def test_backtest_run():
    status, body = _post(
        "/api/backtest/run",
        {"symbol": "SPY", "strategy": "sma_crossover", "days": 180, "initial_capital": 10000},
    )
    assert status == 200, f"Backtest run failed: {status}"
    assert "metrics" in body, "No metrics"
    assert "equity_curve" in body, "No equity curve"


def test_earnings_upcoming():
    status, body = _get("/api/earnings/upcoming?days=90")
    assert status == 200, f"Earnings failed: {status}"
    assert body["summary"]["total"] > 0, "No upcoming earnings"


def test_alerts_list():
    status, body = _get("/api/alerts")
    assert status == 200, f"Alerts list failed: {status}"
    assert "alerts" in body, "No alerts key"


def test_alerts_check():
    status, body = _get("/api/alerts/check")
    assert status == 200, f"Alerts check failed: {status}"
    assert "checked" in body, "No checked key"


# ── Security ─────────────────────────────────────────────────────────

def test_debug_endpoints_disabled():
    status, _ = _get("/docs")
    assert status == 404, f"/docs should return 404, got {status}"


def test_error_responses_sanitized():
    status, body = _get("/api/trading/stocks/INVALIDSTOCK")
    assert status == 404, f"Expected 404, got {status}"
    assert "traceback" not in body.lower(), "Error leaks stack trace"
    assert "File" not in body, "Error leaks file paths"


# ── Run all tests ────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    tests = [
        test_liveness, test_readiness, test_system_status,
        test_dashboard_page, test_trading_hub_page, test_trading_tools_page,
        test_external_factors_page, test_landing_page, test_pricing_page,
        test_market_overview, test_top_movers, test_sectors, test_etfs,
        test_technical_analysis, test_options_data, test_stock_search,
        test_backtest_strategies, test_backtest_run, test_earnings_upcoming,
        test_alerts_list, test_alerts_check,
        test_debug_endpoints_disabled, test_error_responses_sanitized,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {test.__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed}/{passed+failed} passed")
    if failed == 0:
        print("ALL TESTS PASSED")
    sys.exit(1 if failed else 0)
