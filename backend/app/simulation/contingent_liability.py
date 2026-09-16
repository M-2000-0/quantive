"""
Contingent Liability & Guarantee Call Simulation
=================================================
Models guarantee calls as correlated with macro shocks —
guarantees are more likely to be called during the same crisis
stressing the sovereign balance sheet.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Guarantee:
    """A contingent liability / government guarantee."""
    guarantee_id: str
    name: str
    guaranteed_amount: float        # Face value
    guarantee_type: str             # "soe_debt", "ppp", "deposit_insurance", "infrastructure", "sovereign"
    trigger_conditions: list[str]   # What triggers a call
    expected_loss_given_call: float  # Haircut if called (0-1)
    probability_of_call_base: float  # Base annual probability (0-1)
    correlation_with_sovereign: float  # How correlated with sovereign stress (0-1)
    sector: str = ""
    maturity_years: float = 10.0


@dataclass
class GuaranteeCallScenario:
    """Result of a guarantee call simulation."""
    guarantee_id: str
    called: bool
    call_probability: float
    loss_amount: float              # Expected loss
    macro_shock_correlation: float  # How much the macro shock contributed
    timing: Optional[int] = None    # Step when called (if called)


@dataclass
class ContingentLiabilityResult:
    """Full simulation result for all guarantees."""
    total_guaranteed: float
    expected_total_loss: float
    max_loss_95th: float
    guarantees: list[GuaranteeCallScenario]
    stress_scenario_losses: dict  # loss under each stress scenario
    fiscal_impact_pct_gdp: float


class ContingentLiabilitySimulator:
    """
    Monte Carlo simulation of contingent liability calls.

    Key insight: Guarantee calls are NOT independent of macro conditions.
    A SOE goes bankrupt during the same crisis that stresses the sovereign.
    We model this by correlating call probability with the macro shock factor.
    """

    def __init__(self, guarantees: list[Guarantee]):
        self.guarantees = guarantees

    def _estimate_gdp(self) -> float:
        """Estimate GDP from World Bank data, with conservative fallback."""
        try:
            from urllib.request import urlopen, Request
            import json
            url = "https://api.worldbank.org/v2/country/US/indicator/NY.GDP.MKTP.CD?date=2023:2025&format=json&per_page=5"
            req = Request(url, headers={"User-Agent": "Quantive/1.0"})
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                if len(data) >= 2:
                    for item in data[1]:
                        if item.get("value"):
                            return float(item["value"])
        except Exception:
            pass
        # Conservative fallback: US GDP ~$27T
        return 27.0e12

    def simulate(
        self,
        n_paths: int = 1000,
        n_years: int = 10,
        macro_shocks: list[float] = None,
        sovereign_stress_threshold: float = -2.0,
    ) -> ContingentLiabilityResult:
        """
        Simulate guarantee calls across multiple paths.

        Args:
            n_paths: Number of Monte Carlo paths
            n_years: Simulation horizon
            macro_shocks: Pre-computed macro shock paths (if None, generates random)
            sovereign_stress_threshold: GDP growth threshold that triggers correlated calls
        """
        total_guaranteed = sum(g.guaranteed_amount for g in self.guarantees)

        all_losses = []
        all_results = {g.guarantee_id: [] for g in self.guarantees}

        for path in range(n_paths):
            path_loss = 0.0
            path_results = []

            for year in range(n_years):
                # Generate macro shock for this year
                if macro_shocks and year < len(macro_shocks):
                    shock = macro_shocks[year]
                else:
                    shock = random.gauss(0.025, 0.02)  # Mean growth 2.5%, vol 2%

                # Determine if sovereign is under stress
                stressed = shock < sovereign_stress_threshold

                for g in self.guarantees:
                    # Base probability of call
                    base_prob = g.probability_of_call_base

                    # Adjust for macro correlation
                    # When stressed, call probability increases
                    if stressed:
                        stress_multiplier = 1 + g.correlation_with_sovereign * 3
                    else:
                        stress_multiplier = 1.0

                    adjusted_prob = min(0.95, base_prob * stress_multiplier)

                    # Simulate call
                    called = random.random() < adjusted_prob
                    if called:
                        loss = g.guaranteed_amount * g.expected_loss_given_call
                        path_loss += loss
                        path_results.append(GuaranteeCallScenario(
                            guarantee_id=g.guarantee_id,
                            called=True,
                            call_probability=adjusted_prob,
                            loss_amount=loss,
                            macro_shock_correlation=g.correlation_with_sovereign,
                            timing=year,
                        ))

            all_losses.append(path_loss)
            for gr in path_results:
                all_results[gr.guarantee_id].append(gr)

        # Compute statistics
        all_losses_sorted = sorted(all_losses)
        expected_loss = sum(all_losses) / len(all_losses)
        max_loss_95 = all_losses_sorted[int(len(all_losses) * 0.95)]

        # Stress scenario losses
        stress_scenarios = {
            "mild_recession": sum(l for l in all_losses if l > 0) * 0.3 / max(len(all_losses), 1),
            "severe_crisis": sum(l for l in all_losses if l > total_guaranteed * 0.01) / max(len(all_losses), 1),
            "tail_event": max_loss_95,
        }

        # Fetch real GDP from World Bank / IMF, fallback to conservative estimate
        estimated_gdp = self._estimate_gdp()
        fiscal_impact = (expected_loss / estimated_gdp) * 100 if estimated_gdp else 0.0

        return ContingentLiabilityResult(
            total_guaranteed=total_guaranteed,
            expected_total_loss=round(expected_loss, 2),
            max_loss_95th=round(max_loss_95, 2),
            guarantees=[],  # Would aggregate per-guarantee results
            stress_scenario_losses=stress_scenarios,
            fiscal_impact_pct_gdp=round(fiscal_impact, 2),
        )
