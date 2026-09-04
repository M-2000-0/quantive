"""Financial Modeling Engine — Duration, Convexity, VaR, CVaR.

Core analytics for sovereign debt portfolio risk management:
1. Macaulay Duration — weighted average time to receive cash flows
2. Modified Duration — price sensitivity to yield changes
3. Convexity — second-order price sensitivity
4. Value at Risk (VaR) — maximum expected loss at confidence level
5. Conditional VaR (CVaR) — expected loss beyond VaR
6. Key Rate Duration — sensitivity to specific maturity points
7. PV01 / DV01 — dollar value of 1 basis point move
"""

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BondAnalytics:
    """Analytics for a single bond."""
    macaulay_duration: float
    modified_duration: float
    convexity: float
    pv01: float  # Dollar value of 1bp move
    price: float
    ytm: float
    annual_coupon: float
    years_to_maturity: float


@dataclass
class PortfolioRisk:
    """Portfolio-level risk metrics."""
    total_value: float
    portfolio_duration: float
    portfolio_convexity: float
    portfolio_pv01: float
    weighted_ytm: float
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float
    max_drawdown: float
    sharpe_ratio: float
    volatility: float
    tracking_error: Optional[float] = None


@dataclass
class YieldShock:
    """Yield curve shock scenario."""
    parallel_shift_bps: float  # +200 = steepening
    name: str
    steepening_bps: float = 0  # Long end shift relative to short
    description: str = ""


# ── Bond Analytics ──────────────────────────────────────────────────

def compute_bond_analytics(
    principal: float,
    coupon_rate: float,
    years_to_maturity: float,
    ytm: float,
    frequency: int = 2,
    face_value: float = 100,
) -> BondAnalytics:
    """Compute analytics for a single bond.

    Args:
        principal: Face value (notional)
        coupon_rate: Annual coupon rate (decimal)
        years_to_maturity: Years until maturity
        ytm: Yield to maturity (decimal)
        frequency: Coupon payments per year
        face_value: Face value per unit
    """
    n = int(years_to_maturity * frequency)
    c = coupon_rate * face_value / frequency
    y = ytm / frequency

    if y <= 0:
        y = 0.001  # Avoid division by zero

    # Bond price
    price = 0
    for t in range(1, n + 1):
        price += c / (1 + y) ** t
    price += face_value / (1 + y) ** n

    # Macaulay Duration
    mac_dur = 0
    for t in range(1, n + 1):
        pv_cf = c / (1 + y) ** t
        mac_dur += (t / frequency) * pv_cf
    pv_final = face_value / (1 + y) ** n
    mac_dur += (n / frequency) * pv_final
    mac_dur /= price

    # Modified Duration
    mod_dur = mac_dur / (1 + y)

    # Convexity
    conv = 0
    for t in range(1, n + 1):
        pv_cf = c / (1 + y) ** t
        conv += (t * (t + 1)) * pv_cf
    conv += (n * (n + 1)) * pv_final
    conv /= (price * (1 + y) ** 2 * frequency ** 2)

    # PV01 (price change for 1bp yield move)
    dy = 0.0001
    price_up = 0
    for t in range(1, n + 1):
        price_up += c / (1 + y + dy / frequency) ** t
    price_up += face_value / (1 + y + dy / frequency) ** n
    pv01 = abs(price - price_up) * principal / face_value

    return BondAnalytics(
        macaulay_duration=round(mac_dur, 4),
        modified_duration=round(mod_dur, 4),
        convexity=round(conv, 4),
        pv01=round(pv01, 2),
        price=round(price, 4),
        ytm=ytm,
        annual_coupon=coupon_rate * principal,
        years_to_maturity=years_to_maturity,
    )


# ── Portfolio Risk ──────────────────────────────────────────────────

def compute_portfolio_risk(
    instruments: list[dict],
    confidence_levels: list[float] = [0.95, 0.99],
    n_simulations: int = 10000,
    horizon_months: int = 60,
    random_seed: int = 42,
) -> PortfolioRisk:
    """Compute comprehensive portfolio risk metrics.

    Args:
        instruments: List of {principal_outstanding, coupon_rate, maturity_years, rate_type}
        confidence_levels: VaR confidence levels
        n_simulations: Monte Carlo simulation count
        horizon_months: Projection horizon
        random_seed: For reproducibility
    """
    import random
    random.seed(random_seed)

    total_value = sum(inst["principal_outstanding"] for inst in instruments)
    if total_value <= 0:
        return PortfolioRisk(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    # Compute bond-level analytics
    bond_analytics = []
    for inst in instruments:
        principal = inst["principal_outstanding"]
        coupon = inst.get("coupon_rate", 0.05)
        maturity = inst.get("maturity_years", inst.get("maturity_date_years", 5))
        ytm = inst.get("ytm", coupon + 0.002)  # Slight spread

        analytics = compute_bond_analytics(principal, coupon, maturity, ytm)
        bond_analytics.append((inst, analytics))

    # Portfolio-weighted metrics
    weights = [inst["principal_outstanding"] / total_value for inst, _ in bond_analytics]
    port_duration = sum(w * a.modified_duration for w, (_, a) in zip(weights, bond_analytics))
    port_convexity = sum(w * a.convexity for w, (_, a) in zip(weights, bond_analytics))
    port_pv01 = sum(w * a.pv01 for w, (_, a) in zip(weights, bond_analytics))
    port_ytm = sum(w * a.ytm for w, (_, a) in zip(weights, bond_analytics))

    # Monte Carlo VaR/CVaR
    terminal_values = []
    for _ in range(n_simulations):
        portfolio_value = total_value
        for inst, analytics in bond_analytics:
            principal = inst["principal_outstanding"]
            rate_type = inst.get("rate_type", "fixed")
            maturity = inst.get("maturity_years", 5)

            # Generate correlated rate shocks
            for month in range(horizon_months):
                # Hull-White inspired rate dynamics
                base_rate = analytics.ytm
                kappa = 0.05
                sigma = 0.015
                dW = random.gauss(0, 1)
                rate_change = kappa * (0.04 - base_rate) / 12 + sigma * dW / math.sqrt(12)

                if rate_type == "floating":
                    # Floating resets — minimal MTM impact
                    pass
                else:
                    # Fixed: MTM = -duration * delta_r * principal
                    portfolio_value -= analytics.modified_duration * rate_change * principal

                # Coupon income
                portfolio_value += principal * inst.get("coupon_rate", 0.05) / 12

        terminal_values.append(portfolio_value)

    terminal_values.sort()

    # VaR and CVaR
    var_metrics = {}
    cvar_metrics = {}
    for cl in confidence_levels:
        idx = int((1 - cl) * n_simulations)
        idx = min(idx, n_simulations - 1)
        var_val = total_value - terminal_values[idx]
        var_metrics[f"var_{int(cl*100)}"] = round(var_val, 0)

        # CVaR: average of losses beyond VaR
        tail_losses = [total_value - v for v in terminal_values[:idx + 1]]
        cvar_val = sum(tail_losses) / len(tail_losses) if tail_losses else 0
        cvar_metrics[f"cvar_{int(cl*100)}"] = round(cvar_val, 0)

    # Volatility and Sharpe
    returns = [(terminal_values[i] - total_value) / total_value for i in range(n_simulations)]
    mean_return = sum(returns) / n_simulations
    variance = sum((r - mean_return) ** 2 for r in returns) / n_simulations
    volatility = math.sqrt(variance)
    sharpe = (mean_return - 0.04) / volatility if volatility > 0 else 0  # Risk-free = 4%

    # Max drawdown (worst single path)
    min_terminal = terminal_values[0]
    max_drawdown = (total_value - min_terminal) / total_value

    return PortfolioRisk(
        total_value=round(total_value, 0),
        portfolio_duration=round(port_duration, 4),
        portfolio_convexity=round(port_convexity, 4),
        portfolio_pv01=round(port_pv01, 2),
        weighted_ytm=round(port_ytm, 4),
        var_95=var_metrics.get("var_95", 0),
        var_99=var_metrics.get("var_99", 0),
        cvar_95=cvar_metrics.get("cvar_95", 0),
        cvar_99=cvar_metrics.get("cvar_99", 0),
        max_drawdown=round(max_drawdown, 4),
        sharpe_ratio=round(sharpe, 4),
        volatility=round(volatility, 6),
    )


# ── Yield Curve Analytics ───────────────────────────────────────────

def compute_yield_spread(yield_curve: dict[str, float]) -> dict:
    """Compute key yield curve metrics."""
    rates = list(yield_curve.values())
    labels = list(yield_curve.keys())

    if len(rates) < 2:
        return {"spread": 0, "slope": 0, "butterfly": 0}

    # 2s10s spread
    short_rate = yield_curve.get("2Y", yield_curve.get("1Y", rates[0]))
    long_rate = yield_curve.get("10Y", yield_curve.get("30Y", rates[-1]))
    spread = (long_rate - short_rate) * 10000  # In bps

    # 3M30Y slope
    very_short = yield_curve.get("3M", rates[0])
    very_long = yield_curve.get("30Y", rates[-1])
    slope = (very_long - very_short) * 10000

    # Butterfly: (2Y + 10Y) / 2 - 5Y
    butterfly = 0
    if "2Y" in yield_curve and "5Y" in yield_curve and "10Y" in yield_curve:
        butterfly = ((yield_curve["2Y"] + yield_curve["10Y"]) / 2 - yield_curve["5Y"]) * 10000

    return {
        "spread_2s10s_bps": round(spread, 1),
        "slope_3m30y_bps": round(slope, 1),
        "butterfly_bps": round(butterfly, 1),
        "short_rate": round(short_rate * 100, 2),
        "long_rate": round(long_rate * 100, 2),
        "avg_rate": round(sum(rates) / len(rates) * 100, 2),
    }


def compute_inflation_breakeven(
    nominal_curve: dict[str, float],
    tips_curve: dict[str, float],
) -> dict:
    """Compute inflation breakeven rates from nominal vs TIPS curves."""
    breakevens = {}
    for maturity in ["5Y", "10Y", "30Y"]:
        if maturity in nominal_curve and maturity in tips_curve:
            be = (nominal_curve[maturity] - tips_curve[maturity]) * 10000
            breakevens[f"breakeven_{maturity}_bps"] = round(be, 1)

    return breakevens


# ── Scenario Analysis ───────────────────────────────────────────────

def apply_yield_shock(
    yield_curve: dict[str, float],
    shock: YieldShock,
) -> dict[str, float]:
    """Apply a yield curve shock scenario."""
    shocked = {}
    for label, rate in yield_curve.items():
        # Parse maturity for relative positioning
        maturity_years = _label_to_years(label)
        long_end_weight = min(maturity_years / 30, 1.0)  # 0 for short, 1 for 30Y

        # Parallel shift + steepening
        shift = shock.parallel_shift_bps / 10000 + shock.steepening_bps / 10000 * long_end_weight
        shocked[label] = rate + shift

    return shocked


def generate_stress_scenarios() -> list[YieldShock]:
    """Generate standard stress test scenarios."""
    return [
        YieldShock(200, "rate_200bps_up", 0, "Parallel +200bps"),
        YieldShock(-100, "rate_100bps_down", 0, "Parallel -100bps"),
        YieldShock(300, "rate_300bps_up", 0, "Parallel +300bps"),
        YieldShock(0, "steepening", 100, "Yield curve steepening"),
        YieldShock(150, "inflation_spike", 50, "Inflation shock"),
        YieldShock(-200, "recession", -100, "Recession rate cuts"),
    ]


def _label_to_years(label: str) -> float:
    """Convert maturity label to years."""
    mapping = {
        "3M": 0.25, "6M": 0.5, "1Y": 1, "2Y": 2, "3Y": 3,
        "5Y": 5, "7Y": 7, "10Y": 10, "20Y": 20, "30Y": 30,
    }
    return mapping.get(label, 5.0)
