"""Shared in-memory application state."""
from __future__ import annotations

from threading import RLock
from typing import Dict, Optional

from quantive.jobs.manager import JobManager
from quantive.models.instruments import Portfolio
from quantive.models.optimization import OptimizationProblem


class AppState:
    """Thread-safe in-memory stores for portfolios, problems and run outputs."""

    def __init__(self):
        self._lock = RLock()
        self.portfolios: Dict[str, Portfolio] = {}
        self.problems: Dict[str, OptimizationProblem] = {}
        self.runs: Dict[str, dict] = {}
        self.jobs = JobManager(max_workers=2)

    # -- portfolios ----------------------------------------------------------
    def add_portfolio(self, portfolio: Portfolio) -> Portfolio:
        with self._lock:
            self.portfolios[portfolio.id] = portfolio
        return portfolio

    def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        with self._lock:
            return self.portfolios.get(portfolio_id)

    # -- problems -------------------------------------------------------------
    def add_problem(self, problem: OptimizationProblem) -> OptimizationProblem:
        with self._lock:
            self.problems[problem.id] = problem
        return problem

    def get_problem(self, problem_id: str) -> Optional[OptimizationProblem]:
        with self._lock:
            return self.problems.get(problem_id)

    # -- runs -----------------------------------------------------------------
    def set_run(self, problem_id: str, payload: dict) -> None:
        with self._lock:
            self.runs[problem_id] = payload

    def get_run(self, problem_id: str) -> Optional[dict]:
        with self._lock:
            return self.runs.get(problem_id)


state = AppState()