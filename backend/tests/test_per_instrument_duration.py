"""Tests for per-instrument duration math in rate-shock MTM.

The portfolio-average maturity proxy is replaced by principal-weighted
per-instrument modified durations: par-bond closed form for fixed-rate
bonds, next-reset (0.25y) for floaters.
"""
import math

from app.ai.portfolio_context import (
    FLOATER_DURATION_YEARS,
    compute_rate_shock,
    instrument_effective_duration,
    par_bond_modified_duration,
)


# ── Par-bond closed form ──────────────────────────────────────────────

def test_par_bond_duration_below_maturity():
    # A 10y 4% par bond has modified duration ≈ 8.11y < 10y.
    d = par_bond_modified_duration(10.0, 4.0)
    assert math.isclose(d, 8.111, abs_tol=0.01)
    assert d < 10.0


def test_zero_coupon_duration_equals_maturity():
    assert math.isclose(par_bond_modified_duration(10.0, 0.0), 10.0)


def test_short_bonds_duration_close_to_maturity():
    # Half-year bond: duration ≈ maturity (single cash flow).
    d = par_bond_modified_duration(0.5, 4.25)
    assert 0.4 < d <= 0.5


def test_long_30y_bond_duration():
    d = par_bond_modified_duration(30.0, 4.75)
    # Closed form for 30y 4.75% ≈ 15.5y — far below the 30y maturity.
    assert 14.0 < d < 17.0
    assert d < 30.0


def test_monotonic_in_maturity_and_inverse_in_coupon():
    assert par_bond_modified_duration(20, 4) > par_bond_modified_duration(10, 4)
    assert par_bond_modified_duration(10, 6) < par_bond_modified_duration(10, 4)


def test_floater_sits_at_next_reset():
    assert instrument_effective_duration(29.3, 4.75, "floating_rate_note") == FLOATER_DURATION_YEARS


def test_fixed_uses_par_form():
    d = instrument_effective_duration(10.0, 4.0, "sovereign_bond")
    assert math.isclose(d, 8.111, abs_tol=0.01)


def test_degenerate_inputs():
    assert par_bond_modified_duration(0, 4) == 0.0
    assert par_bond_modified_duration(-5, 4) == 0.0
    assert par_bond_modified_duration(None, None) == 0.0


# ── Rate shock uses the duration aggregate ────────────────────────────

def _snap(duration, **extra):
    snap = {
        "total_principal": 1_000_000_000.0,
        "wtd_coupon_pct": 4.5,
        "wtd_maturity_years": 12.4,
        "floating_principal": 100_000_000.0,
        "nearest_maturities": [],
    }
    if duration is not None:
        snap["wtd_duration_years"] = duration
    snap.update(extra)
    return snap


def test_mtm_uses_per_instrument_duration():
    out = compute_rate_shock(_snap(7.5), 50.0)
    assert out["mtm_impact"] == -37_500_000.0  # 7.5 * 0.005 * 1B
    assert out["duration_source"] == "per-instrument"
    assert "Σ −Dᵢ×Δy×Pᵢ" in out["method"]


def test_legacy_snapshot_falls_back_to_maturity_proxy():
    out = compute_rate_shock(_snap(None), 50.0)
    assert out["mtm_impact"] == -62_000_000.0  # 12.4 * 0.005 * 1B
    assert out["duration_source"] == "weighted-maturity proxy (legacy)"
    assert "weighted maturity" in out["method"]


def test_duration_floor_prevents_zero_mtm():
    out = compute_rate_shock(_snap(0.0), 100.0)
    assert out["mtm_impact"] < 0


def test_floater_heavy_book_low_duration():
    # A 1B book that is mostly floaters should have D ≈ 0.25 → tiny MTM.
    out = compute_rate_shock(_snap(0.3), 100.0)
    assert out["mtm_impact"] == -3_000_000.0
