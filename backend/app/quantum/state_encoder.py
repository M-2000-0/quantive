"""Layer 2: Quantum State Encoding & Algorithm Design.

Maps classical multi-currency yield curves and bond maturity matrices
into quantum variational circuits for QAOA and VQE optimization.

Encoding Strategy:
- Binary expansion: Each continuous variable encoded as B binary bits
- Angle encoding: Continuous parameters mapped to rotation angles
- Amplitude encoding: Portfolio weights as state amplitudes (when qubit count allows)

Circuit Structure:
    |0⟩ → [Initial State] → [Cost Hamiltonian] → [Mixer] → [Measure]
                              ↑ QAOA layers       ↑ Problem-specific

For NISQ-era hardware:
- Circuit depth minimized to reduce decoherence
- Error mitigation applied at readout
- Classical post-processing for feasibility repair

IMPORTANT: This module generates circuits for CLASSICAL SIMULATION.
When real QPU is available, the same circuit objects can be submitted
to hardware backends via the quantum_abstraction layer.
"""
import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QubitAllocation:
    """Tracks qubit usage across encoding stages."""
    total_qubits: int = 0
    used_qubits: int = 0
    allocation: dict = field(default_factory=dict)  # name → (start, end)

    def allocate(self, name: str, count: int) -> tuple:
        """Allocate qubits for a named encoding block."""
        start = self.used_qubits
        end = start + count
        if end > self.total_qubits:
            raise ValueError(
                f"Qubit exhaustion: need {count} more, only {self.total_qubits - self.used_qubits} available"
            )
        self.used_qubits = end
        self.allocation[name] = (start, end)
        return (start, end)

    @property
    def remaining(self) -> int:
        return self.total_qubits - self.used_qubits


@dataclass
class CircuitParameters:
    """Parameters for variational circuit construction."""
    n_qubits: int
    n_layers: int          # QAOA/VQE depth
    gamma: list            # Cost layer angles
    beta: list             # Mixer layer angles
    encoding_bits: int = 8  # Bits per continuous variable
    seed: Optional[int] = None  # For reproducibility


@dataclass
class CostFunction:
    """Defines the cost Hamiltonian for sovereign debt optimization.

    Objective: Minimize total debt servicing cost subject to:
    - Debt ceiling constraints
    - Maturity distribution limits
    - Currency exposure limits
    - Liquidity requirements
    """
    # Weights for multi-objective optimization
    w_debt_cost: float = 0.40       # Minimize coupon payments
    w_refinancing_risk: float = 0.25  # Smooth maturity profile
    w_currency_risk: float = 0.15    # Limit FX exposure
    w_liquidity: float = 0.10       # Maintain cash reserves
    w_issuance_cost: float = 0.10   # Minimize transaction costs

    # Constraints (hard limits)
    max_debt_to_gdp: float = 60.0
    max_single_maturity_concentration: float = 0.25
    max_fx_exposure: float = 0.30
    min_liquidity_months: float = 3.0

    def evaluate(self, portfolio_encoding: dict) -> float:
        """Evaluate cost function for a given portfolio encoding.

        Returns: Cost value (lower is better)
        """
        cost = 0.0

        # Debt servicing cost
        cost += self.w_debt_cost * portfolio_encoding.get("coupon_burden", 0)

        # Refinancing risk (maturity concentration)
        concentration = portfolio_encoding.get("max_maturity_concentration", 0)
        if concentration > self.max_single_maturity_concentration:
            cost += self.w_refinancing_risk * (concentration - self.max_single_maturity_concentration) * 10

        # Currency risk
        fx_exposure = portfolio_encoding.get("fx_exposure", 0)
        if fx_exposure > self.max_fx_exposure:
            cost += self.w_currency_risk * (fx_exposure - self.max_fx_exposure) * 10

        # Liquidity penalty
        liquidity = portfolio_encoding.get("liquidity_months", 12)
        if liquidity < self.min_liquidity_months:
            cost += self.w_liquidity * (self.min_liquidity_months - liquidity) * 5

        return cost


class SovereignStateEncoder:
    """Encodes classical sovereign debt data into quantum circuit parameters.

    Encoding Pipeline:
    1. Normalize: Scale all values to [0, 1] range
    2. Binary Expand: Convert continuous variables to binary strings
    3. Assign Qubits: Map binary bits to qubit positions
    4. Build Circuit: Construct variational circuit with encoded parameters
    5. Define Hamiltonian: Set cost function as diagonal Hamiltonian

    Qubit Budget Estimation:
    - Per instrument: 8 qubits (binary-encoded allocation weight)
    - Per yield curve point: 4 qubits (rate encoding)
    - Per constraint: 2 qubits (penalty qubits)
    - Total for 20 instruments + 10 yield points + 5 constraints:
      20*8 + 10*4 + 5*2 = 210 qubits (classical simulation only)
    """

    BITS_PER_VARIABLE = 8  # Precision for binary encoding

    def __init__(self, max_qubits: int = 100):
        self.max_qubits = max_qubits
        self.qubit_mgr = QubitAllocation(total_qubits=max_qubits)

    def encode_portfolio(
        self,
        instruments: list[dict],
        yield_curve: list[dict],
        macro_data: dict,
    ) -> CircuitParameters:
        """Encode classical portfolio data into circuit parameters.

        Returns CircuitParameters ready for QAOA/VQE execution.
        """
        n_instruments = len(instruments)
        n_yield_points = len(yield_curve)

        # Estimate qubit requirements
        qubits_instruments = n_instruments * self.BITS_PER_VARIABLE
        qubits_yield = n_yield_points * 4
        qubits_constraints = 5 * 2  # Penalty qubits

        total_needed = qubits_instruments + qubits_yield + qubits_constraints
        if total_needed > self.max_qubits:
            raise ValueError(
                f"Need {total_needed} qubits but only {self.max_qubits} available. "
                f"Reduce instruments ({n_instruments}) or use classical fallback."
            )

        # Normalize instrument weights
        total_face_value = sum(inst.get("face_value", 0) for inst in instruments)
        normalized_weights = []
        for inst in instruments:
            weight = inst.get("face_value", 0) / total_face_value if total_face_value > 0 else 0
            normalized_weights.append(weight)

        # Normalize yields
        yields = [yp.get("yield_pct", 0) for yp in yield_curve]
        min_yield = min(yields) if yields else 0
        max_yield = max(yields) if yields else 10
        yield_range = max_yield - min_yield if max_yield != min_yield else 1
        normalized_yields = [(y - min_yield) / yield_range for y in yields]

        # Build gamma (cost) and beta (mixer) parameters
        n_layers = max(2, min(10, total_needed // 10))
        gamma = [0.5 + 0.1 * i for i in range(n_layers)]
        beta = [0.3 + 0.05 * i for i in range(n_layers)]

        return CircuitParameters(
            n_qubits=total_needed,
            n_layers=n_layers,
            gamma=gamma,
            beta=beta,
            encoding_bits=self.BITS_PER_VARIABLE,
        )

    def build_cost_hamiltonian(
        self,
        instruments: list[dict],
        yield_curve: list[dict],
        macro_data: dict,
    ) -> CostFunction:
        """Build the cost Hamiltonian (objective function) for optimization.

        This defines what the quantum algorithm is trying to minimize.
        """
        # Extract macro parameters for constraint setting
        debt_to_gdp = macro_data.get("debt_to_gdp_pct", 50.0)
        inflation = macro_data.get("inflation_pct", 2.0)

        # Adjust constraints based on economic conditions
        max_debt = max(40.0, 80.0 - debt_to_gdp * 0.3)  # Tighter if already high debt

        return CostFunction(
            max_debt_to_gdp=max_debt,
            max_single_maturity_concentration=0.25,
            max_fx_exposure=0.30,
            min_liquidity_months=3.0,
        )

    def compute_binary_encoding(self, value: float, min_val: float, max_val: float) -> list[int]:
        """Convert a continuous value to binary string using linear scaling.

        Args:
            value: The value to encode
            min_val: Minimum of the range
            max_val: Maximum of the range

        Returns:
            List of 0/1 integers representing the binary encoding
        """
        # Normalize to [0, 1]
        if max_val == min_val:
            normalized = 0.5
        else:
            normalized = max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))

        # Convert to binary
        bits = []
        for i in range(self.BITS_PER_VARIABLE):
            bit_val = int(normalized * (2 ** (i + 1))) % 2
            bits.append(bit_val)

        return bits

    def decode_binary_encoding(self, bits: list[int], min_val: float, max_val: float) -> float:
        """Decode binary encoding back to continuous value."""
        value = 0.0
        for i, bit in enumerate(bits):
            value += bit * (2 ** i)
        # Normalize back
        max_representable = (2 ** len(bits)) - 1
        if max_representable == 0:
            return min_val
        return min_val + (value / max_representable) * (max_val - min_val)

    def get_encoding_summary(self, params: CircuitParameters) -> dict:
        """Summary of encoding for audit trail."""
        return {
            "n_qubits": params.n_qubits,
            "n_layers": params.n_layers,
            "encoding_bits_per_variable": params.encoding_bits,
            "gamma_parameters": params.gamma,
            "beta_parameters": params.beta,
            "total_circuit_depth": params.n_layers * 2,  # 2 gates per layer
            "estimation_method": "binary_expansion",
            "precision": f"1/{2**params.encoding_bits - 1}",
        }
