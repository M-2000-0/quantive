import logging

import numpy as np

logger = logging.getLogger("quantive.optimization")


class ScenarioGenerator:
    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def generate_rate_scenarios(
        self, base_rate: float, num_scenarios: int, horizon_years: float,
        volatility: float = 0.02, drift: float = 0.0
    ) -> np.ndarray:
        dt = 1 / 12
        steps = int(horizon_years * 12)
        rates = np.zeros((num_scenarios, steps + 1))
        rates[:, 0] = base_rate
        for t in range(1, steps + 1):
            dW = self.rng.standard_normal(num_scenarios) * np.sqrt(dt)
            rates[:, t] = rates[:, t - 1] + drift * dt + volatility * dW
            rates[:, t] = np.maximum(rates[:, t], -0.05)
        return rates

    def generate_inflation_scenarios(
        self, mean: float, num_scenarios: int, horizon_years: float,
        volatility: float = 0.01
    ) -> np.ndarray:
        dt = 1 / 12
        steps = int(horizon_years * 12)
        inflation = np.zeros((num_scenarios, steps + 1))
        inflation[:, 0] = mean
        for t in range(1, steps + 1):
            dW = self.rng.standard_normal(num_scenarios) * np.sqrt(dt)
            inflation[:, t] = inflation[:, t - 1] + (mean - inflation[:, t - 1]) * 0.1 * dt + volatility * dW
            inflation[:, t] = np.maximum(inflation[:, t], -0.1)
        return inflation

    def generate_fx_scenarios(
        self, base_rate: float, num_scenarios: int, horizon_years: float,
        volatility: float = 0.1
    ) -> np.ndarray:
        dt = 1 / 12
        steps = int(horizon_years * 12)
        fx = np.zeros((num_scenarios, steps + 1))
        fx[:, 0] = base_rate
        for t in range(1, steps + 1):
            dW = self.rng.standard_normal(num_scenarios) * np.sqrt(dt)
            fx[:, t] = fx[:, t - 1] * np.exp(-0.5 * volatility ** 2 * dt + volatility * dW)
        return fx

    def generate_all_scenarios(self, config: dict) -> dict:
        num = config.get("num_scenarios", 10000)
        horizon = config.get("horizon_years", 5.0)
        rate_vol = config.get("rate_volatility", 0.02)
        rate_drift = config.get("rate_drift", 0.0)
        infl_mean = config.get("inflation_mean", 0.03)
        infl_vol = config.get("inflation_volatility", 0.01)
        fx_vol = config.get("fx_volatility", 0.1)

        base_rate = 0.05
        base_fx = 1.0
        rates = self.generate_rate_scenarios(base_rate, num, horizon, rate_vol, rate_drift)
        inflation = self.generate_inflation_scenarios(infl_mean, num, horizon, infl_vol)
        fx = self.generate_fx_scenarios(base_fx, num, horizon, fx_vol)

        return {
            "num_scenarios": num,
            "horizon_years": horizon,
            "interest_rates": rates,
            "inflation": inflation,
            "fx_rates": fx,
            "step_size": 1 / 12,
        }


class BaseSolver:
    def __init__(self, name: str):
        self.name = name

    def solve(self, instruments: list[dict], objectives: dict, constraints: dict,
              scenarios: dict, seed: int = 42) -> dict:
        raise NotImplementedError


class GreedySolver(BaseSolver):
    def __init__(self):
        super().__init__("greedy")

    def solve(self, instruments: list[dict], objectives: dict, constraints: dict,
              scenarios: dict, seed: int = 42) -> dict:
        if not instruments:
            return {"allocations": {}, "objective_value": 0.0, "feasible": True, "iterations": 0}

        total_principal = sum(inst.get("principal_outstanding", 0) for inst in instruments)
        if total_principal == 0:
            return {"allocations": {}, "objective_value": 0.0, "feasible": True, "iterations": 0}

        opt_type = objectives.get("type", "minimize_cost")
        allocations = {}

        if opt_type == "minimize_cost":
            scored = sorted(instruments, key=lambda x: x.get("coupon_rate", 0))
        elif opt_type == "minimize_risk":
            scored = sorted(instruments, key=lambda x: abs(x.get("spread_bps", 0)))
        elif opt_type == "minimize_duration":
            scored = sorted(instruments, key=lambda x: self._duration_years(x))
        else:
            scored = instruments

        remaining = total_principal
        for inst in scored:
            alloc = min(inst.get("principal_outstanding", 0), remaining)
            if alloc > 0:
                allocations[inst["id"]] = alloc
                remaining -= alloc
            if remaining <= 0:
                break

        total_cost = sum(
            allocations.get(inst["id"], 0) * inst.get("coupon_rate", 0)
            for inst in instruments if inst["id"] in allocations
        )
        avg_duration = np.mean([self._duration_years(inst) for inst in instruments if inst["id"] in allocations]) if allocations else 0

        return {
            "allocations": allocations,
            "objective_value": total_cost,
            "feasible": remaining <= 0.01 * total_principal,
            "iterations": len(instruments),
            "metrics": {
                "total_cost": total_cost,
                "avg_duration": float(avg_duration),
                "utilization": 1.0 - (remaining / total_principal if total_principal > 0 else 0),
            },
        }

    def _duration_years(self, inst: dict) -> float:
        try:
            from datetime import datetime
            mat = datetime.strptime(inst.get("maturity_date", "2030-01-01"), "%Y-%m-%d")
            now = datetime.now()
            return max((mat - now).days / 365.25, 0.1)
        except (ValueError, TypeError):
            return 5.0


class MeanVarianceSolver(BaseSolver):
    def __init__(self):
        super().__init__("mean_variance")

    def solve(self, instruments: list[dict], objectives: dict, constraints: dict,
              scenarios: dict, seed: int = 42) -> dict:
        from scipy.optimize import minimize

        n = len(instruments)
        if n == 0:
            return {"allocations": {}, "objective_value": 0.0, "feasible": True, "iterations": 0}

        coupons = np.array([inst.get("coupon_rate", 0) for inst in instruments])
        spreads = np.array([inst.get("spread_bps", 0) / 10000 for inst in instruments])
        principals = np.array([inst.get("principal_outstanding", 0) for inst in instruments])

        expected_returns = coupons - spreads
        cov_matrix = np.diag(spreads ** 2 + 0.001)
        total = principals.sum()

        risk_aversion = objectives.get("risk_aversion", 1.0)

        def objective(w):
            ret = np.dot(w, expected_returns)
            risk = w @ cov_matrix @ w
            return -(ret - risk_aversion * risk)

        bounds = [(0, p / total) for p in principals]
        cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        x0 = principals / total

        result = minimize(objective, x0, method="SLSQP", bounds=bounds, constraints=cons,
                         options={"maxiter": 1000, "ftol": 1e-12})

        alloc_values = result.x * total
        allocations = {inst["id"]: float(alloc_values[i]) for i, inst in enumerate(instruments)}

        return {
            "allocations": allocations,
            "objective_value": float(-result.fun),
            "feasible": result.success,
            "iterations": result.nit if hasattr(result, "nit") else 0,
            "metrics": {
                "expected_return": float(np.dot(result.x, expected_returns)),
                "portfolio_risk": float(result.x @ cov_matrix @ result.x),
                "sharpe_ratio": float(np.dot(result.x, expected_returns) / max(np.sqrt(result.x @ cov_matrix @ result.x), 1e-10)),
            },
        }


class ScenarioBasedSolver(BaseSolver):
    def __init__(self):
        super().__init__("scenario_based")

    def solve(self, instruments: list[dict], objectives: dict, constraints: dict,
              scenarios: dict, seed: int = 42) -> dict:
        from scipy.optimize import minimize

        n = len(instruments)
        if n == 0:
            return {"allocations": {}, "objective_value": 0.0, "feasible": True, "iterations": 0}

        principals = np.array([inst.get("principal_outstanding", 0) for inst in instruments])
        coupons = np.array([inst.get("coupon_rate", 0) for inst in instruments])
        total = principals.sum()
        if total == 0:
            return {"allocations": {}, "objective_value": 0.0, "feasible": True, "iterations": 0}

        rates = scenarios.get("interest_rates", np.full((100, 12), 0.05))
        n_scenarios = rates.shape[0]
        sample_n = min(n_scenarios, 200)
        rng = np.random.default_rng(seed)
        sample_indices = rng.choice(n_scenarios, size=sample_n, replace=False) if n_scenarios > sample_n else np.arange(n_scenarios)
        sampled_rates = rates[sample_indices]

        def portfolio_costs(weights, r):
            avg_coupon = np.dot(weights, coupons)
            last_rates = r[:, -1] if r.ndim > 1 else np.array([r[-1]])
            return total * (avg_coupon + (np.mean(last_rates) - np.mean(coupons)) * 0.1)

        def objective(w):
            costs = np.array([portfolio_costs(w, sampled_rates[s]) for s in range(sample_n)])
            expected = np.mean(costs)
            var95 = np.percentile(costs, 95)
            return 0.5 * expected + 0.5 * var95

        bounds = [(0, p / total) for p in principals]
        cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        weights = principals / total

        result = minimize(objective, weights, method="SLSQP", bounds=bounds, constraints=cons,
                         options={"maxiter": 500})

        alloc_values = result.x * total
        allocations = {inst["id"]: float(alloc_values[i]) for i, inst in enumerate(instruments)}

        all_costs = np.array([portfolio_costs(result.x, rates[s]) for s in range(min(n_scenarios, 500))])

        return {
            "allocations": allocations,
            "objective_value": float(result.fun),
            "feasible": result.success,
            "iterations": result.nit if hasattr(result, "nit") else 0,
            "metrics": {
                "expected_cost": float(np.mean(all_costs)),
                "var_95": float(np.percentile(all_costs, 95)),
                "worst_case": float(np.max(all_costs)),
            },
        }


def get_solver(name: str) -> BaseSolver:
    solvers = {
        "greedy": GreedySolver(),
        "mean_variance": MeanVarianceSolver(),
        "scenario_based": ScenarioBasedSolver(),
    }
    return solvers.get(name, GreedySolver())


class BenchmarkRunner:
    def __init__(self):
        self.solvers = [GreedySolver(), MeanVarianceSolver(), ScenarioBasedSolver()]

    def run_benchmarks(self, instruments: list[dict], objectives: dict, constraints: dict,
                       scenarios: dict, seed: int = 42) -> list[dict]:
        import time
        results = []
        for solver in self.solvers:
            start = time.time()
            try:
                result = solver.solve(instruments, objectives, constraints, scenarios, seed)
                elapsed = time.time() - start
                results.append({
                    "solver_name": solver.name,
                    "execution_time_seconds": round(elapsed, 4),
                    "objective_value": result["objective_value"],
                    "feasible": result.get("feasible", True),
                    "iterations": result.get("iterations", 0),
                    "metrics": result.get("metrics", {}),
                })
            except Exception as e:
                elapsed = time.time() - start
                results.append({
                    "solver_name": solver.name,
                    "execution_time_seconds": round(elapsed, 4),
                    "objective_value": float("inf"),
                    "feasible": False,
                    "iterations": 0,
                    "metrics": {"error": str(e)},
                })
        return results


class StressTestRunner:
    def run_stress_test(self, instruments: list[dict], allocations: dict,
                        scenarios: dict, seed: int = 42) -> dict:
        stress_shocks = {
            "rate_shock_up_200bps": {"rate_change": 0.02},
            "rate_shock_down_100bps": {"rate_change": -0.01},
            "inflation_spike": {"inflation_change": 0.05},
            "currency_devaluation": {"fx_shock": -0.15},
            "combined_adverse": {"rate_change": 0.02, "inflation_change": 0.03, "fx_shock": -0.1},
        }

        results = {}
        for scenario_name, shock in stress_shocks.items():
            total_cost_impact = 0.0
            for inst in instruments:
                alloc = allocations.get(inst["id"], 0)
                if alloc > 0:
                    coupon = inst.get("coupon_rate", 0)
                    rate_impact = shock.get("rate_change", 0) * alloc * 0.3
                    inflation_impact = shock.get("inflation_change", 0) * alloc * 0.2
                    fx_impact = shock.get("fx_shock", 0) * alloc * 0.1 if inst.get("currency", "USD") != "USD" else 0
                    total_cost_impact += coupon * alloc + rate_impact + inflation_impact + fx_impact

            results[scenario_name] = {
                "cost_impact": round(total_cost_impact, 2),
                "severity": "high" if abs(total_cost_impact) > sum(
                    allocations.get(inst["id"], 0) * inst.get("coupon_rate", 0)
                    for inst in instruments if allocations.get(inst["id"], 0) > 0
                ) * 0.1 else "medium" if abs(total_cost_impact) > 0 else "low",
            }

        return results


class StrategyGenerator:
    def generate_strategies(self, instruments: list[dict], benchmarks: list[dict],
                            scenarios: dict, seed: int = 42) -> list[dict]:
        strategies = []

        strategy_templates = [
            {"name": "Cost Minimizer", "type": "minimize_cost", "description": "Prioritizes lowest borrowing cost"},
            {"name": "Risk Averse", "type": "minimize_risk", "description": "Minimizes exposure to rate volatility"},
            {"name": "Balanced", "type": "mean_variance", "description": "Balances cost and risk objectives"},
            {"name": "Stress Resilient", "type": "scenario_based", "description": "Optimizes across scenario distribution"},
        ]

        for i, template in enumerate(strategy_templates):
            solver = get_solver(template["type"])
            objectives = {"type": template["type"], "risk_aversion": 1.0 + i * 0.5}
            result = solver.solve(instruments, objectives, {}, scenarios, seed)

            total_alloc = sum(result["allocations"].values())
            metrics = result.get("metrics", {})
            metrics["total_allocated"] = total_alloc
            metrics["num_instruments"] = len([v for v in result["allocations"].values() if v > 0])

            strategies.append({
                "name": template["name"],
                "description": template["description"],
                "allocations": result["allocations"],
                "metrics": metrics,
                "rank": i + 1,
            })

        return strategies
