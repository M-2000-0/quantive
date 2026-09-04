@dataclass
class SimulationConfig:
    """Configuration for Monte Carlo simulation."""
    n_paths: int = 1000
    n_steps: int = 252
    horizon_years: float = 10.0
    dt: float = 1/252
    rate_kappa: float = 0.15
    rate_theta: float = 0.04
    rate_sigma: float = 0.01
    rate_model: str = "vasicek"
    fx_s0: float = 1.08
    fx_mu: float = 0.0
    fx_sigma: float = 0.08
    growth_mu: float = 0.025
    growth_sigma: float = 0.02
    correlation: CorrelationMatrix = field(default_factory=CorrelationMatrix)
    use_student_t: bool = False
    student_t_nu: float = 4.0
    lookback_years: int = 10


@dataclass
class SimulationResult:
    """Results from Monte Carlo simulation."""
    config: SimulationConfig
    rate_paths: list[list[float]]
    fx_paths: list[list[float]]
    growth_paths: list[list[float]]
    primary_balance_paths: list[list[float]]
    rate_mean: list[float]
    rate_p5: list[float]
    rate_p10: list[float]
    rate_p25: list[float]
    rate_p50: list[float]
    rate_p75: list[float]
    rate_p90: list[float]
    rate_p95: list[float]
    fx_mean: list[float]
    fx_p5: list[float]
    fx_p10: list[float]
    fx_p25: list[float]
    fx_p50: list[float]
    fx_p75: list[float]
    fx_p90: list[float]
    fx_p95: list[float]
    growth_mean: list[float]
    growth_p5: list[float]
    growth_p10: list[float]
    growth_p25: list[float]
    growth_p50: list[float]
    growth_p75: list[float]
    growth_p90: list[float]
    growth_p95: list[float]
    debt_service_median: list[float]
    debt_service_p5: list[float]
    debt_service_p95: list[float]
    debt_to_gdp_median: list[float]
    debt_to_gdp_p5: list[float]
    debt_to_gdp_p10: list[float]
    debt_to_gdp_p25: list[float]
    debt_to_gdp_p50: list[float]
    debt_to_gdp_p75: list[float]
    debt_to_gdp_p90: list[float]
    debt_to_gdp_p95: list[float]
    debt_to_revenue_median: list[float]
    debt_to_revenue_p5: list[float]
    debt_to_revenue_p95: list[float]


class MonteCarloEngine:
    """Production Monte Carlo simulation engine for sovereign debt sustainability."""

    def __init__(self, config: SimulationConfig = None):
        self.config = config or SimulationConfig()

    def simulate(self, portfolio: Optional[object] = None) -> SimulationResult:
        """Run full correlated Monte Carlo simulation."""
        chol = self.config.correlation.cholesky()
        if self.config.rate_model == "cir":
            from .engine import CIRModel as _CIRHelper
            rate_helper = _CIRHelper(kappa=self.config.rate_kappa,
                                     theta=self.config.rate_theta,
                                     sigma=self.config.rate_sigma,
                                     r0=self.config.rate_theta)
        elif self.config.rate_model == "hull_white":
            rate_helper = VasicekModel(kappa=self.config.rate_kappa,
                                       theta=self.config.rate_theta,
                                       sigma=self.config.rate_sigma,
                                       r0=self.config.rate_theta)
        else:
            rate_helper = VasicekModel(kappa=self.config.rate_kappa,
                                       theta=self.config.rate_theta,
                                       sigma=self.config.rate_sigma,
                                       r0=self.config.rate_theta)
        innovations = StudentTInnovations(nu=self.config.student_t_nu) if self.config.use_student_t else None
        n = self.config.n_paths
        steps = self.config.n_steps
        dt = self.config.dt

        rate_paths = []
        fx_paths = []
        growth_paths = []
        primary_balance_paths = []

        for _ in range(n):
            rate_path = [self.config.rate_theta]
            fx_path = [self.config.fx_s0]
            growth_path = [self.config.growth_mu]
            primary_path = [self.config.growth_mu]
            r = self.config.rate_theta
            fx = self.config.fx_s0
            g = self.config.growth_mu
            pb = self.config.growth_mu
            for _ in range(steps):
                if innovations:
                    draws = correlated_draws(1, chol, use_student_t=True, nu=self.config.student_t_nu)
                else:
                    draws = correlated_draws(1, chol)
                z_r, z_fx, z_g, z_pb = draws[0]
                if self.config.rate_model == "cir":
                    r_pos = max(r, 0)
                    dr = (self.config.rate_kappa * (self.config.rate_theta - r_pos) * dt +
                          self.config.rate_sigma * math.sqrt(r_pos) * z_r * math.sqrt(dt))
                elif self.config.rate_model == "hull_white":
                    dr = (self.config.rate_kappa * (self.config.rate_theta - r) * dt +
                          self.config.rate_sigma * z_r * math.sqrt(dt))
                else:
                    dr = (self.config.rate_kappa * (self.config.rate_theta - r) * dt +
                          self.config.rate_sigma * z_r * math.sqrt(dt))
                r = r + dr
                dfx = fx * (self.config.fx_mu * dt + self.config.fx_sigma * z_fx * math.sqrt(dt))
                fx = fx + dfx
                dg = (self.config.growth_mu - g) * 0.1 * dt + self.config.growth_sigma * z_g * math.sqrt(dt)
                g = g + dg
                dpb = (self.config.growth_mu - pb) * 0.05 * dt + self.config.growth_sigma * 0.8 * z_pb * math.sqrt(dt)
                pb = pb + dpb
                rate_path.append(r)
                fx_path.append(fx)
                growth_path.append(g)
                primary_path.append(pb)
                rate_paths.append(rate_path)
                fx_paths.append(fx_path)
                growth_paths.append(growth_path)
                primary_balance_paths.append(primary_path)

        def percentile(paths, p):
            return [sorted(path)[int(len(path) * p / 100)] for path in zip(*paths)]

        rate_mean = [statistics.mean(path) for path in zip(*rate_paths)]
        rate_p5 = percentile(rate_paths, 5)
        rate_p10 = percentile(rate_paths, 10)
        rate_p25 = percentile(rate_paths, 25)
        rate_p50 = percentile(rate_paths, 50)
        rate_p75 = percentile(rate_paths, 75)
        rate_p90 = percentile(rate_paths, 90)
        rate_p95 = percentile(rate_paths, 95)

        fx_mean = [statistics.mean(path) for path in zip(*fx_paths)]
        fx_p5 = percentile(fx_paths, 5)
        fx_p10 = percentile(fx_paths, 10)
        fx_p25 = percentile(fx_paths, 25)
        fx_p50 = percentile(fx_paths, 50)
        fx_p75 = percentile(fx_paths, 75)
        fx_p90 = percentile(fx_paths, 90)
        fx_p95 = percentile(fx_paths, 95)

        growth_mean = [statistics.mean(path) for path in zip(*growth_paths)]
        growth_p5 = percentile(growth_paths, 5)
        growth_p10 = percentile(growth_paths, 10)
        growth_p25 = percentile(growth_paths, 25)
        growth_p50 = percentile(growth_paths, 50)
        growth_p75 = percentile(growth_paths, 75)
        growth_p90 = percentile(growth_paths, 90)
        growth_p95 = percentile(growth_paths, 95)

        pb_mean = [statistics.mean(path) for path in zip(*primary_balance_paths)]
        pb_p5 = percentile(primary_balance_paths, 5)
        pb_p10 = percentile(primary_balance_paths, 10)
        pb_p25 = percentile(primary_balance_paths, 25)
        pb_p50 = percentile(primary_balance_paths, 50)
        pb_p75 = percentile(primary_balance_paths, 75)
        pb_p90 = percentile(primary_balance_paths, 90)
        pb_p95 = percentile(primary_balance_paths, 95)

        debt_service_median = []
        debt_service_p5 = []
        debt_service_p95 = []
        debt_to_gdp_median = []
        debt_to_gdp_p5 = []
        debt_to_gdp_p10 = []
        debt_to_gdp_p25 = []
        debt_to_gdp_p50 = []
        debt_to_gdp_p75 = []
        debt_to_gdp_p90 = []
        debt_to_gdp_p95 = []
        debt_to_revenue_median = []
        debt_to_revenue_p5 = []
        debt_to_revenue_p95 = []

        if portfolio is not None:
            init_dg = getattr(portfolio, 'initial_debt_gdp', 55.0)
            init_dr = getattr(portfolio, 'initial_debt_revenue', 15.0)
            init_pr = getattr(portfolio, 'initial_principal', 100.0)
            for i in range(steps + 1):
                rates_at_t = [p[i] for p in rate_paths]
                growth_at_t = [p[i] for p in growth_paths]
                fx_at_t = [p[i] for p in fx_paths]
                pb_at_t = [p[i] for p in primary_balance_paths]
                ds_vals = []
                dg_vals = []
                dr_vals = []
                for j in range(n):
                    r_at_t = rates_at_t[j] / 100
                    real_g = growth_at_t[j] / 100
                    fx_ef = (fx_at_t[j] - self.config.fx_s0) / self.config.fx_s0 * 0.3
                    dtg = init_dg * (1 + r_at_t - real_g + fx_ef * 0.1) ** (i * dt if i > 0 else 1)
                    dg_vals.append(dtg)
                    ds_vals.append(r_at_t * init_pr * (1 + r_at_t) ** (i * dt if i > 0 else 1) / 100
                    nom_g = real_g + r_at_t / 4
                    rev_t = init_dr * (1 + nom_g) ** i if i > 0 else init_dr
                    if rev_t > 0: dr_vals.append(dtg / (rev_t / 100 * 100))
                    else: dr_vals.append(0)
                dg_sorted = sorted(dg_vals)
                ds_sorted = sorted(ds_vals)
                debt_to_gdp_median.append(statistics.mean(dg_vals))
                debt_to_gdp_p5.append(dg_sorted[int(n * 0.05)])
                debt_to_gdp_p10.append(dg_sorted[int(n * 0.10)])
                debt_to_gdp_p25.append(dg_sorted[int(n * 0.25)])
                debt_to_gdp_p50.append(dg_sorted[int(n * 0.50)])
                debt_to_gdp_p75.append(dg_sorted[int(n * 0.75)])
                debt_to_gdp_p90.append(dg_sorted[int(n * 0.90)])
                debt_to_gdp_p95.append(dg_sorted[int(n * 0.95)])
                debt_service_median.append(statistics.mean(ds_vals))
                debt_service_p5.append(ds_sorted[int(n * 0.05)])
                debt_service_p95.append(ds_sorted[int(n * 0.95)])
                debt_to_revenue_median.append(statistics.mean(dr_vals))
                debt_to_revenue_p5.append(min(dr_vals))
                debt_to_revenue_p95.append(max(dr_vals))

        return SimulationResult(
            config=self.config,
            rate_paths=rate_paths,
            fx_paths=fx_paths,
            growth_paths=growth_paths,
            primary_balance_paths=primary_balance_paths,
            rate_mean=rate_mean,
            rate_p5=rate_p5,
            rate_p10=rate_p10,
            rate_p25=rate_p25,
            rate_p50=rate_p50,
            rate_p75=rate_p75,
            rate_p90=rate_p90,
            rate_p95=rate_p95,
            fx_mean=fx_mean,
            fx_p5=fx_p5,
            fx_p10=fx_p10,
            fx_p25=fx_p25,
            fx_p50=fx_p50,
            fx_p75=fx_p75,
            fx_p90=fx_p90,
            fx_p95=fx_p95,
            growth_mean=growth_mean,
            growth_p5=growth_p5,
            growth_p10=growth_p10,
            growth_p25=growth_p25,
            growth_p50=growth_p50,
            growth_p75=growth_p75,
            growth_p90=growth_p90,
            growth_p95=growth_p95,
            debt_service_median=debt_service_median,
            debt_service_p5=debt_service_p5,
            debt_service_p95=debt_service_p95,
            debt_to_gdp_median=debt_to_gdp_median,
            debt_to_gdp_p5=debt_to_gdp_p5,
            debt_to_gdp_p10=debt_to_gdp_p10,
            debt_to_gdp_p25=debt_to_gdp_p25,
            debt_to_gdp_p50=debt_to_gdp_p50,
            debt_to_gdp_p75=debt_to_gdp_p75,
            debt_to_gdp_p90=debt_to_gdp_p90,
            debt_to_gdp_p95=debt_to_gdp_p95,
            debt_to_revenue_median=debt_to_revenue_median,
            debt_to_revenue_p5=debt_to_revenue_p5,
            debt_to_revenue_p95=debt_to_revenue_p95,
        )


# Backtest Validation

class BacktestValidator:
    """
    Validate simulation against historical reality.

    Runs simulation from a historical start date and checks if
    the confidence bands would have bracketed actual outcomes.
    """

    def validate_from_2007(self) -> dict:
        """
        Backtest: Run simulation from January 2007 and check whether
        actual subsequent outcomes fall within the model's generated
        confidence bands.

        Historical facts (Jan 2007 - Dec 2009):
        - US 10Y yield: 4.7% → 2.1% (with crisis peak ~5% then crash to 2.1%)
        - EUR/USD: 1.32 → 1.26 (with peak at 1.60 in 2008 Q3)
        - US GDP growth: +2.9% → -2.5% (Q4 2008)
        - Primary balance deteriorated significantly during crisis
        """
        from .engine import MonteCarloEngine, SimulationConfig
        config = SimulationConfig(n_paths=5000, n_steps=756, rate_theta=0.047,
                                  rate_sigma=0.015, fx_s0=1.32, fx_sigma=0.10,
                                  growth_mu=0.025, growth_sigma=0.025,
                                  use_student_t=True, student_t_nu=3.0, lookback_years=10)
        engine = MonteCarloEngine(config)
        result = engine.simulate()

        actual_rate_end = 0.021  # 2.1% (Dec 2008)
        actual_fx_end = 1.26     # EUR/USD (Dec 2009)
        actual_growth_end = -0.025  # -2.5% GDP growth

        rate_band = (result.rate_p5[-1], result.rate_p95[-1])
        fx_band = (result.fx_p5[-1], result.fx_p95[-1])
        growth_band = (result.growth_p5[-1], result.growth_p95[-1])

        rate_caught = rate_band[0] <= actual_rate_end <= rate_band[1]
        fx_caught = fx_band[0] <= actual_fx_end <= fx_band[1]
        growth_caught = growth_band[0] <= actual_growth_end <= growth_band[1]

        notes = []
        if not rate_caught:
            notes.append(f"Rate end {actual_rate_end*100:.1f}% outside band [{rate_band[0]*100:.1f}%, {rate_band[1]*100:.1f}%]")
        if not fx_caught:
            notes.append(f"FX end {actual_fx_end:.4f} outside band [{fx_band[0]:.4f}, {fx_band[1]:.4f}]")
        if not growth_caught:
            notes.append(f"Growth end {actual_growth_end*100:.1f}% outside band [{growth_band[0]*100:.1f}%, {growth_band[1]*100:.1f}%]")

        return {
            "test": "Backtest from January 2007 (3-year horizon)",
            "horizon": "2007-2010 (Financial Crisis)",
            "rate_95_band": f"[{rate_band[0]*100:.1f}%, {rate_band[1]*100:.1f}%]",
            "actual_rate": f"{actual_rate_end*100:.1f}%",
            "rate_caught": rate_caught,
            "fx_95_band": f"[{fx_band[0]:.4f}, {fx_band[1]:.4f}]",
            "actual_fx": f"{actual_fx_end:.4f}",
            "fx_caught": fx_caught,
            "growth_95_band": f"[{growth_band[0]*100:.1f}%, {growth_band[1]*100:.1f}%]",
            "actual_growth": f"{actual_growth_end*100:.1f}%",
            "growth_caught": growth_caught,
            "overall": "PASS" if rate_caught and fx_caught and growth_caught else "NEEDS CALIBRATION",
            "recommendation": "" if rate_caught and fx_caught and growth_caught
            else "Increase volatility parameters, add jump-diffusion, or extend lookback window",
        }

    def validate_debt_sustainability(self, result: SimulationResult, initial_debt_gdp: float = 55.0) -> dict:
        """Validate debt-to-GDP outcomes against fiscal sustainability rules."""
        horizon_idx = len(result.debt_to_gdp_median) - 1
        median_horizon_dg = result.debt_to_gdp_median[horizon_idx] if horizon_idx >= 0 else 55.0
        p95_horizon_dg = result.debt_to_gdp_p95[horizon_idx] if horizon_idx >= 0 and horizon_idx < len(result.debt_to_gdp_p95) else initial_debt_gdp

        sustainability_flag = p95_horizon_dg < 100.0
        within_60_median = median_horizon_dg < 60.0
        within_60_p95 = p95_horizon_dg < 60.0

        return {
            "test": "Debt sustainability validation",
            "initial_debt_gdp": initial_debt_gdp,
            "median_horizon_debt_gdp": f"{median_horizon_dg:.1f}%",
            "p95_horizon_debt_gdp": f"{p95_horizon_dg:.1f}%",
            "sustainability_flag": sustainability_flag,
            "within_60pct_median": within_60_median,
            "within_60pct_p95": within_60_p95,
            "flag": "PASS" if sustainability_flag else "FAIL",
            "notes": "Median debt-to-GDP trajectory is sustainable; "
                     "95th percentile should not exceed 100% under normal assumptions",
        }