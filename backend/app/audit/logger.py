import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

AUDIT_BASE_DIR = Path(__file__).parent.parent / "logs" / "audit"
AUDIT_BASE_DIR.mkdir(parents=True, exist_ok=True)


class AuditLogger:
    """Append-only audit logger writing JSONL files per day."""

    @staticmethod
    def _today_file() -> Path:
        return AUDIT_BASE_DIR / f"{datetime.utcnow().strftime('%Y-%m-%d')}.jsonl"

    @staticmethod
    def log(
        event: str,
        data: Dict[str, Any],
        user: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Append a single audit entry."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "user": user,
            "ip_address": ip_address,
            "data": data,
        }
        log_file = AuditLogger._today_file()
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    @staticmethod
    def log_optimization_start(
        problem_id: str,
        user: Optional[str],
        portfolio_id: str,
        scenario_count: int,
        ip_address: Optional[str] = None,
    ) -> None:
        AuditLogger.log(
            event="optimization_start",
            data={
                "problem_id": problem_id,
                "portfolio_id": portfolio_id,
                "scenario_count": scenario_count,
            },
            user=user,
            ip_address=ip_address,
        )

    @staticmethod
    def log_optimization_complete(
        result_id: str,
        user: Optional[str],
        feasible: bool,
        objective_value: float,
        runtime: float,
        ip_address: Optional[str] = None,
    ) -> None:
        AuditLogger.log(
            event="optimization_complete",
            data={
                "result_id": result_id,
                "feasible": feasible,
                "objective_value": objective_value,
                "runtime_seconds": runtime,
            },
            user=user,
            ip_address=ip_address,
        )

    @staticmethod
    def log_solver_used(
        solver_name: str,
        solver_type: str,
        backend: str,
        problem_id: str,
        user: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        AuditLogger.log(
            event="solver_used",
            data={
                "solver_name": solver_name,
                "solver_type": solver_type,
                "execution_backend": backend,
                "problem_id": problem_id,
            },
            user=user,
            ip_address=ip_address,
        )