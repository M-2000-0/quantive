"""Solver tests: output structure, feasibility, determinism, QUBO matrix."""
from __future__ import annotations

import numpy as np
import pytest

from quantive.models.enums import ExecutionBackend, SolverType
from quantive.solvers.registry import available_solvers, get_solver

SOLVERS = ["milp", "highs", "simulated_annealing", "qubo"]


def _fast_config(problem, name):
    cfg = problem.solver_config.model_copy()
    if name != "milp":
        cfg.anneal_iterations = 3000
    return cfg


@pytest.mark.parametrize("name", SOLVERS)
def test_solver_returns_valid_result(portfolio, problem, scenarios, spec, name):
    solver = get_solver(name)
    cfg = _fast_config(problem, name)
    res = solver.solve(spec, cfg)
    assert res.allocation
    assert res.objective_value >= 0
    assert res.financing_cost >= 0
    assert res.risk_metrics is not None
    assert res.objective_decomposition
    assert res.constraint_status
    assert res.runtime >= 0


@pytest.mark.parametrize("name", SOLVERS)
def test_solver_sums_to_requirement(portfolio, problem, scenarios, spec, name):
    solver = get_solver(name)
    cfg = _fast_config(problem, name)
    res = solver.solve(spec, cfg)
    total = sum(res.allocation.values())
    assert total == pytest.approx(spec.financing_requirement, rel=1e-3)


@pytest.mark.parametrize("name", SOLVERS)
def test_solver_respects_capacities(portfolio, problem, scenarios, spec, name):
    solver = get_solver(name)
    cfg = _fast_config(problem, name)
    res = solver.solve(spec, cfg)
    for iid, amount in res.allocation.items():
        cap = spec.portfolio.instrument_by_id(iid).capacity
        assert amount <= cap * 1.001 + 1e-6


def test_milp_is_feasible_and_optimal(spec, problem):
    res = get_solver("milp").solve(spec, problem.solver_config)
    assert res.feasible
    assert "globally optimal" in res.optimality_note


def test_milp_reports_correct_metadata(spec, problem):
    res = get_solver("milp").solve(spec, problem.solver_config)
    assert res.solver_type == SolverType.CLASSICAL
    assert res.execution_backend == ExecutionBackend.CLASSICAL_CPU


def test_solver_type_distinctions(spec, problem):
    assert get_solver("milp").solver_type == SolverType.CLASSICAL
    assert get_solver("simulated_annealing").solver_type == SolverType.HEURISTIC
    assert get_solver("qubo").solver_type == SolverType.QUANTUM_INSPIRED
    assert get_solver("qubo").execution_backend == ExecutionBackend.SIMULATOR
    assert get_solver("qubo").execution_backend != ExecutionBackend.REAL_QUANTUM_HARDWARE


def test_unknown_solver_raises():
    with pytest.raises(KeyError):
        get_solver("nonexistent")


def test_available_solvers():
    assert set(available_solvers()) == set(SOLVERS)


def test_sa_deterministic_with_seed(portfolio, problem, scenarios, spec):
    cfg = _fast_config(problem, "simulated_annealing")
    a = get_solver("simulated_annealing").solve(spec, cfg)
    b = get_solver("simulated_annealing").solve(spec, cfg)
    assert a.allocation == b.allocation


def test_qubo_deterministic_with_seed(portfolio, problem, scenarios, spec):
    cfg = _fast_config(problem, "qubo")
    a = get_solver("qubo").solve(spec, cfg)
    b = get_solver("qubo").solve(spec, cfg)
    assert a.allocation == b.allocation


def test_qubo_matrix_shape(portfolio, problem, scenarios, spec):
    from quantive.solvers.qubo import QUBOSolver

    cfg = problem.solver_config
    Q = QUBOSolver().to_qubo_matrix(spec, cfg)
    nb = spec.n_instruments * cfg.qubo_bits
    assert Q.shape == (nb, nb)
    # symmetric
    assert np.allclose(Q, Q.T)


def test_qubo_matrix_reproduces_energy(portfolio, problem, scenarios, spec):
    """For a fixed bit vector, q^T Q q (core) equals the quadratic core energy.

    ``to_qubo_matrix`` reproduces the polynomial core: the linear cost/risk
    terms plus the squared debt-capacity penalty. The peak-year refinancing
    term is a max (not quadratic) and is excluded from the matrix, so the test
    compares only against the core terms (constants dropped, as in the matrix).
    """
    from quantive.solvers.qubo import QUBOSolver

    solver = QUBOSolver()
    cfg = problem.solver_config
    B = cfg.qubo_bits
    Q = solver.to_qubo_matrix(spec, cfg)
    rng = np.random.default_rng(0)
    bits = rng.integers(0, 2, size=spec.n_instruments * B)
    steps = solver._steps(spec.capacity, B)
    x = np.zeros(spec.n_instruments)
    for i in range(spec.n_instruments):
        for b in range(B):
            x[i] += steps[i] * (2 ** b) * bits[i * B + b]
    w_cost, _w_refi, w_ir, w_fx = spec.weights
    R = spec.financing_requirement
    lin = float(np.dot(x, w_cost * (spec.cost_matrix @ spec.probabilities) + w_ir * spec.ir_risk + w_fx * spec.fx_risk))
    pen_core = spec.penalty * ((x.sum() - R) ** 2 - R ** 2)
    energy = lin + pen_core
    assert energy == pytest.approx(bits @ Q @ bits)


def test_heuristic_repairs_to_feasibility(portfolio, problem, scenarios, spec):
    cfg = _fast_config(problem, "simulated_annealing")
    res = get_solver("simulated_annealing").solve(spec, cfg)
    assert res.feasible


def test_qubo_repairs_to_feasibility(portfolio, problem, scenarios, spec):
    cfg = _fast_config(problem, "qubo")
    res = get_solver("qubo").solve(spec, cfg)
    assert res.feasible


def test_milp_infeasible_problem_reported(spec, problem, scenarios):
    """An impossible problem must be reported infeasible, not faked.

    Raising requirement above total instrument capacity makes the problem
    infeasible by construction.
    """
    over = problem.model_copy(deep=True)
    over.financing_requirement = spec.capacity.sum() * 2.0
    from quantive.objectives.spec import build_spec

    over_spec = build_spec(spec.portfolio, over, scenarios)
    res = get_solver("milp").solve(over_spec, over.solver_config)
    assert res.feasible is False
    assert "INFEASIBLE" in res.optimality_note