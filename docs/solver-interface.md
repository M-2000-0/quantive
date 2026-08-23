# Solver Interface

All solvers implement the same contract, so the pipeline, benchmark, and API
treat them identically.

## Interface

```python
class SolverInterface(ABC):
    name: str               # stable solver id, e.g. "milp_cbc"
    solver_type: SolverType # CLASSICAL | QUANTUM_INSPIRED | QUANTUM_SIMULATOR
    execution_backend: ExecutionBackend

    @abstractmethod
    def solve(self, spec: ProblemSpec, config: SolverConfiguration) -> SolveResult:
        ...
```

`SolveResult` (built by `build_result` in `solvers/base.py`) carries:

- `allocation` — `{instrument_id: amount}` summing to the financing requirement
  when feasible;
- `objective_value` — the canonical composite objective evaluated by the spec;
- `financing_cost`, `risk_metrics`, `objective_decomposition`,
  `constraint_status` — the evaluated strategy profile;
- `feasible` — derived from `ProblemSpec.feasibility(x)`, **never** assumed;
- `solver`, `solver_type`, `execution_backend` — provenance, so the API can
  distinguish classical vs quantum-inspired vs simulator results;
- `runtime`, `iterations`, `objective_evaluations`, `optimality_note`,
  `metadata`.

Solvers register themselves in `solvers/registry.py`:

```python
get_solver("milp")              # -> MILPSolver
get_solver("simulated_annealing")
get_solver("qubo")
```

## Backends

| Solver | `name` | `solver_type` | `execution_backend` | Optimality |
|---|---|---|---|---|
| MILP + CBC | `milp_cbc` | `CLASSICAL` | `CLASSICAL_CPU` | Globally optimal (LP) |
| Simulated annealing | `simulated_annealing` | `CLASSICAL` | `CLASSICAL_CPU` | None guaranteed |
| QUBO annealing | `qubo_annealing` | `QUANTUM_INSPIRED` | `SIMULATOR` | None guaranteed |

## Honest reporting of quantum claims

Quantive never fabricates a quantum advantage. The rules:

1. Every result carries `solver_type` and `execution_backend`. The QUBO path is
   `QUANTUM_INSPIRED` on a `SIMULATOR` (a classical CPU), and its
   `optimality_note` states this explicitly.
2. Results are produced by the classical simulator that ships with this package;
   nothing is ever claimed to come from real quantum hardware.
3. No solver is ever assumed superior to another; the benchmark measures them
   and the ranking is data-driven (`docs/benchmarking.md`).
4. If a real QPU backend were added later, it would be a new
   `ExecutionBackend.QUANTUM_HARDWARE` value with its own provenance label —
   the data model already separates the algorithm family from the hardware.

## The three engines in detail

### MILP (`solvers/milp.py`)

Builds the linear model in PuLP (objective terms from `docs/optimization-model.md`,
constraints 1:1 from the spec) and solves with CBC under a time limit. Returns
`INFEASIBLE` with an empty allocation when the model is impossible, and reports
`Optimal` only when CBC proves global optimality.

### Simulated annealing (`solvers/heuristic.py`)

Starts from a maturity-ladder allocation and proposes continuous pairwise moves
that preserve `Σx = R` (so the equality never needs per-iteration projection),
accepting worse moves with a Metropolis criterion under an exponentially cooled
temperature. Each move is evaluated with the canonical objective and the fast
vectorized violation magnitude. Ends with a deterministic classical repair.

### QUBO (`solvers/qubo.py`)

1. Each variable is encoded as `B` bits with step size
   `cap_i / (2^B - 1)`.
2. The **polynomial core** of the energy — weighted cost + interest-rate risk +
   FX risk (linear) plus the squared debt-capacity penalty (quadratic) — is a
   genuine quadratic form in the bits; `to_qubo_matrix()` returns the exact `Q`
   with `E(q) = qᵀQq`. Peak-year refinancing risk (a max term) and the
   one-sided bound constraints (hinge penalties) are evaluated directly by the
   annealer, the standard practical treatment in QUBO-based optimization.
3. Annealing runs over the bits on a classical simulator with a seeded RNG.
4. The best bit vector is projected to the box-simplex and passed through the
   deterministic classical repair, so reported results are always feasible or
   explicitly flagged.

The separation of the exact quadratic core from the piecewise-linear / hinge
terms is intentional and documented, and the energy used for annealing always
matches the canonical objective plus soft penalties (see `_energy_from_aggregates`).

## Configuration

`SolverConfiguration` fields (all optional, with defaults):

- `solver` — backend id;
- `seed` — RNG seed for stochastic solvers and scenario generation;
- `time_limit_seconds` — MILP time limit;
- `anneal_iterations`, `annealing_initial_temp`, `annealing_cooling_rate` —
  simulated-annealing schedule;
- `qubo_bits` — bits per variable in the QUBO encoding;
- `penalty` — weight of the soft debt-capacity penalty in stochastic solvers.