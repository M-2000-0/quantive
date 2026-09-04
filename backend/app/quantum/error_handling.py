"""Layer 6: Error Handling Matrix.

Defines specific mitigation triggers for every failure mode in the
quantum-classical hybrid pipeline.

Failure Categories:
1. Quantum Hardware: Decoherence, gate errors, readout errors
2. Algorithmic: Barren plateaus, local minima, convergence failure
3. Data Pipeline: Missing data, stale data, corrupted feeds
4. Security: PQC handshake failure, key compromise, tampering
5. Infrastructure: QPU unavailability, network partition, storage failure

Each failure has:
- Detection trigger (how we know it happened)
- Severity (impact on recommendation quality)
- Mitigation (what we do about it)
- Recovery (how we restore normal operation)
- Escalation (who gets notified)
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class FailureCategory(str, Enum):
    QUANTUM_HARDWARE = "quantum_hardware"
    ALGORITHMIC = "algorithmic"
    DATA_PIPELINE = "data_pipeline"
    SECURITY = "security"
    INFRASTRUCTURE = "infrastructure"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MitigationRule:
    category: FailureCategory
    failure_mode: str
    detection_trigger: str
    severity: Severity
    mitigation: str
    recovery: str
    escalation: str
    max_retries: int = 3
    timeout_seconds: int = 300


class ErrorHandlingMatrix:
    """Comprehensive error handling for the hybrid quantum-classical platform.

    Every potential failure is mapped to:
    1. A detection mechanism
    2. An automated mitigation
    3. A recovery procedure
    4. An escalation path
    """

    RULES = [
        # ── Quantum Hardware Failures ──────────────────────────────
        MitigationRule(
            category=FailureCategory.QUANTUM_HARDWARE,
            failure_mode="Decoherence / Qubit Instability",
            detection_trigger="Circuit output variance exceeds 2x baseline over 10 consecutive runs",
            severity=Severity.HIGH,
            mitigation="Reduce circuit depth by 50%. Switch to shorter-depth QAOA variant. Apply Zero-Noise Extrapolation.",
            recovery="Recalibrate qubits. If persistent, route to classical fallback.",
            escalation="Notify quantum operations team within 15 minutes",
            max_retries=2,
        ),
        MitigationRule(
            category=FailureCategory.QUANTUM_HARDWARE,
            failure_mode="Gate Error Rate Spike",
            detection_trigger="Two-qubit gate error rate > 5% (measured via randomized benchmarking)",
            severity=Severity.CRITICAL,
            mitigation="Immediately pause quantum jobs. Queue recalibration. Reroute pending jobs to classical solver.",
            recovery="Wait for recalibration completion. Verify error rates return to <1%.",
            escalation="Page on-call quantum engineer immediately",
        ),
        MitigationRule(
            category=FailureCategory.QUANTUM_HARDWARE,
            failure_mode="QPU Unavailability",
            detection_trigger="QPU health check fails or job queue timeout > 60 seconds",
            severity=Severity.MEDIUM,
            mitigation="Automatic failover to classical GPU cluster. No user-facing impact.",
            recovery="Monitor QPU status. Resume quantum jobs when availability confirmed.",
            escalation="Log incident. Notify ops team if outage > 1 hour.",
        ),

        # ── Algorithmic Failures ───────────────────────────────────
        MitigationRule(
            category=FailureCategory.ALGORITHMIC,
            failure_mode="Barren Plateau",
            detection_trigger="Gradient variance < 1e-6 for 100 consecutive iterations",
            severity=Severity.HIGH,
            mitigation="Switch to hardware-efficient ansatz. Reduce parameter count. Try different initialization.",
            recovery="If barren plateau persists after 3 attempts, fall back to classical SA.",
            escalation="Log for algorithm research review",
        ),
        MitigationRule(
            category=FailureCategory.ALGORITHMIC,
            failure_mode="Local Minima Convergence",
            detection_trigger="Energy improvement < 1e-8 for 200 iterations but gradient still nonzero",
            severity=Severity.MEDIUM,
            mitigation="Increase mixer temperature. Add random restarts from different initial points. Try parallel tempering.",
            recovery="Compare best result across restarts. Use best feasible solution found.",
            escalation="None — standard operating behavior",
        ),
        MitigationRule(
            category=FailureCategory.ALGORITHMIC,
            failure_mode="Convergence Timeout",
            detection_trigger="Solve time exceeds 300 seconds without convergence",
            severity=Severity.MEDIUM,
            mitigation="Return best-so-far solution. Mark as 'partial convergence'. Run classical post-processing for feasibility repair.",
            recovery="Increase timeout for next run. Consider problem decomposition.",
            escalation="None if partial result is feasible",
        ),
        MitigationRule(
            category=FailureCategory.ALGORITHMIC,
            failure_mode="Infeasible Solution",
            detection_trigger="Constraint violation detected in final solution (debt ceiling, concentration, FX limits)",
            severity=Severity.HIGH,
            mitigation="Run feasibility repair algorithm. If repair fails, apply penalty-based reoptimization.",
            recovery="Verify repaired solution satisfies all hard constraints.",
            escalation="Notify analyst if hard constraint cannot be satisfied",
        ),

        # ── Data Pipeline Failures ─────────────────────────────────
        MitigationRule(
            category=FailureCategory.DATA_PIPELINE,
            failure_mode="Missing Data Feed",
            detection_trigger="Expected data source returns null or HTTP error for > 15 minutes",
            severity=Severity.HIGH,
            mitigation="Use last known valid data with staleness warning. Flag optimization result as 'based on stale data'.",
            recovery="Monitor source. Resume normal ingestion when feed restores. Backfill missing data.",
            escalation="Alert data operations team if stale data used in optimization",
        ),
        MitigationRule(
            category=FailureCategory.DATA_PIPELINE,
            failure_mode="Corrupted Data Detected",
            detection_trigger="Schema validation fails or anomaly score > 50 on input data",
            severity=Severity.CRITICAL,
            mitigation="Reject corrupted data. Do NOT feed to optimizer. Queue for human review.",
            recovery="Manual data correction. Re-run optimization with validated data.",
            escalation="Immediate alert to data quality team",
        ),
        MitigationRule(
            category=FailureCategory.DATA_PIPELINE,
            failure_mode="Data Poisoning Attempt",
            detection_trigger="Cross-source conflict detected or input outside 3-sigma historical range",
            severity=Severity.CRITICAL,
            mitigation="Block data from entering optimization. Log as security incident. Preserve evidence.",
            recovery="Manual investigation. Verify data provenance. Restore from trusted backup.",
            escalation="Immediate alert to security team and compliance officer",
        ),

        # ── Security Failures ──────────────────────────────────────
        MitigationRule(
            category=FailureCategory.SECURITY,
            failure_mode="PQC Handshake Failure",
            detection_trigger="ML-KEM decapsulation fails or ML-DSA signature verification fails",
            severity=Severity.CRITICAL,
            mitigation="Reject request immediately. Do not fall back to classical crypto. Log as potential attack.",
            recovery="Verify client identity through out-of-band channel. Issue new keypair.",
            escalation="Immediate alert to security operations center",
        ),
        MitigationRule(
            category=FailureCategory.SECURITY,
            failure_mode="Key Compromise Detected",
            detection_trigger="Anomalous key usage pattern or unauthorized key access attempt",
            severity=Severity.CRITICAL,
            mitigation="Immediately revoke compromised key. Rotate all session keys. Invalidate all active sessions.",
            recovery="Generate new keypair from HSM. Re-establish trust with all clients.",
            escalation="Incident response team activated. Legal counsel notified.",
        ),
        MitigationRule(
            category=FailureCategory.SECURITY,
            failure_mode="Audit Chain Tampering",
            detection_trigger="Hash chain verification fails (broken link detected)",
            severity=Severity.CRITICAL,
            mitigation="System enters lockdown. No new optimizations until investigation complete. Preserve all evidence.",
            recovery="Forensic investigation. Restore from verified backup. Rebuild chain if legitimate modification.",
            escalation="Immediate alert to CISO and legal counsel",
        ),

        # ── Infrastructure Failures ────────────────────────────────
        MitigationRule(
            category=FailureCategory.INFRASTRUCTURE,
            failure_mode="Database Connection Loss",
            detection_trigger="3 consecutive connection failures to primary database",
            severity=Severity.HIGH,
            mitigation="Switch to read replica. Queue write operations. Use cached data for reads.",
            recovery="Monitor primary. Resume when connectivity restored. Flush write queue.",
            escalation="DBA on-call notified within 5 minutes",
        ),
        MitigationRule(
            category=FailureCategory.INFRASTRUCTURE,
            failure_mode="Storage Failure",
            detection_trigger="Write operation fails or disk usage > 95%",
            severity=Severity.CRITICAL,
            mitigation="Pause new data ingestion. Alert for immediate remediation. Use backup storage.",
            recovery="Expand storage or migrate to healthy node. Verify data integrity post-recovery.",
            escalation="Infrastructure team immediate page",
        ),
    ]

    @classmethod
    def get_rules_for_category(cls, category: FailureCategory) -> list[MitigationRule]:
        return [r for r in cls.RULES if r.category == category]

    @classmethod
    def get_rules_for_severity(cls, severity: Severity) -> list[MitigationRule]:
        return [r for r in cls.RULES if r.severity == severity]

    @classmethod
    def get_all_failure_modes(cls) -> dict:
        """Summary of all failure modes for documentation."""
        summary = {}
        for category in FailureCategory:
            rules = cls.get_rules_for_category(category)
            summary[category.value] = {
                "count": len(rules),
                "failure_modes": [
                    {
                        "mode": r.failure_mode,
                        "severity": r.severity.value,
                        "trigger": r.detection_trigger,
                    }
                    for r in rules
                ],
            }
        return summary

    @classmethod
    def get_critical_path(cls) -> list[dict]:
        """Get all CRITICAL severity failure modes — the ones that can destroy the system."""
        return [
            {
                "failure": r.failure_mode,
                "trigger": r.detection_trigger,
                "mitigation": r.mitigation,
                "escalation": r.escalation,
            }
            for r in cls.RULES if r.severity == Severity.CRITICAL
        ]
