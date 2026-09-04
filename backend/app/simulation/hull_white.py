"""
Hull-White One-Factor Model
============================
dr = [θ(t) - a·r]dt + σdW

Fits today's yield curve exactly while adding stochastic volatility.
More realistic than Vasicek for debt management because it's curve-consistent.
"""

import math
import random
from dataclasses import dataclass


@dataclass
class HullWhiteParams:
    """Hull-White model parameters."""
    a: float = 0.03          # Mean-reversion speed (typically 0.01-0.10)
    sigma: float = 0.007     # Volatility (typically 0.005-0.02)
    r0: float = 0.0425       # Current short rate


class HullWhiteModel:
    """
    Hull-White one-factor model for curve-consistent simulation.

    Unlike Vasicek (which uses a constant long-term mean θ),
    Hull-White uses a time-dependent θ(t) that is calibrated to
    fit today's observed yield curve exactly.

    θ(t) = ∂f(0,t)/∂t + a·f(0,t) + σ²/(2a)·(1 - e^(-2at))

    where f(0,t) is the instantaneous forward rate from today's curve.
    """

    def __init__(self, params: HullWhiteParams = None):
        self.params = params or HullWhiteParams()

    def calibrate_theta(self, maturities: list[float], rates: list[float]) -> list[tuple[float, float]]:
        """
        Calibrate θ(t) to fit observed yield curve.

        Args:
            maturities: Time points in years [0.5, 1, 2, 5, 10, ...]
            rates: Corresponding zero rates [0.045, 0.042, ...]

        Returns:
            List of (time, theta) pairs for interpolation.
        """
        a = self.params.a
        sigma = self.params.sigma

        # Fit polynomial to observed rates to get smooth f(0,t)
        # Using cubic spline approximation
        n = len(maturities)
        thetas = []

        for i in range(n - 1):
            t = maturities[i]
            dt = maturities[i + 1] - maturities[i]

            # Forward rate approximation: f(0,t) ≈ -∂ln(P)/∂t ≈ r(t) + t·∂r/∂t
            r_t = rates[i]
            r_next = rates[i + 1]
            dr_dt = (r_next - r_t) / dt if dt > 0 else 0

            # Forward rate
            f_t = r_t + t * dr_dt

            # Theta calibration
            theta = dr_dt + a * f_t + (sigma ** 2 / (2 * a)) * (1 - math.exp(-2 * a * t))
            thetas.append((t, theta))

        return thetas

    def simulate(
        self,
        steps: int = 252,
        dt: float = 1/252,
        n_paths: int = 1000,
        maturities: list[float] = None,
        rates: list[float] = None,
    ) -> list[list[float]]:
        """
        Simulate interest rate paths using Hull-White model.

        Uses analytical solution for better accuracy than Euler discretization:
        r(t+Δt) = r(t)·e^(-aΔt) + α(t+Δt) - α(t)·e^(-aΔt) + σ√((1-e^(-2aΔt))/(2a))·Z

        where α(t) is the deterministic shift calibrated to fit the yield curve.
        """
        a = self.params.a
        sigma = self.params.sigma
        r0 = self.params.r0

        # Calibrate theta from observed curve
        if maturities and rates and len(maturities) >= 3:
            theta_table = self.calibrate_theta(maturities, rates)
        else:
            # Use constant theta (reduces to Vasicek)
            theta_table = [(0, a * r0)]

        def get_theta(t):
            """Interpolate theta at time t."""
            if not theta_table:
                return a * r0
            # Linear interpolation
            for i in range(len(theta_table) - 1):
                t1, th1 = theta_table[i]
                t2, th2 = theta_table[i + 1]
                if t1 <= t <= t2:
                    frac = (t - t1) / (t2 - t1) if t2 > t1 else 0
                    return th1 + frac * (th2 - th1)
            return theta_table[-1][1]

        # Simulate paths
        paths = []
        for _ in range(n_paths):
            rates_path = [r0]
            r = r0

            for step in range(steps):
                t = step * dt
                theta = get_theta(t)

                # Analytical solution
                Z = random.gauss(0, 1)
                drift = r * math.exp(-a * dt) + (theta / a) * (1 - math.exp(-a * dt))
                vol = sigma * math.sqrt((1 - math.exp(-2 * a * dt)) / (2 * a))

                r = drift + vol * Z
                rates_path.append(r)

            paths.append(rates_path)

        return paths

    def zero_rate(self, t: float, r: float) -> float:
        """
        Compute zero rate at maturity t given current short rate r.

        P(0,t) = exp(-r·(1-e^(-at))/a - σ²/(4a³)·(1-e^(-at))² - r·t)
        """
        a = self.params.a
        sigma = self.params.sigma

        if t <= 0:
            return r

        avg_rate = r * (1 - math.exp(-a * t)) / (a * t) if t > 0 else r
        vol_adj = (sigma ** 2 / (4 * a ** 3)) * (1 - math.exp(-a * t)) ** 2 / t if t > 0 else 0

        return avg_rate + vol_adj
