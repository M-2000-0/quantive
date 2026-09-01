"""Trust foundation tests — Pillars 2, 3, 5, 6, 9."""
import pytest
from datetime import datetime, timezone, timedelta

from quantive.trust.audit import AuditTrail, ActionType
from quantive.trust.approval import ApprovalWorkflow, ApprovalLevel, ProposalStatus
from quantive.trust.assumptions import AssumptionRegistry
from quantive.trust.explainability import (
    ExplainabilityEngine, AssumptionRef, DataSource, Risk, Alternative,
)


# ── Audit Trail ──────────────────────────────────────────────────────

class TestAuditTrail:
    def test_record_and_count(self):
        trail = AuditTrail()
        e = trail.record(actor="analyst-1", action=ActionType.CREATE, target_type="portfolio", target_id="p-1")
        assert trail.count == 1
        assert e.actor == "analyst-1"
        assert e.action == ActionType.CREATE

    def test_append_only(self):
        trail = AuditTrail()
        trail.record(actor="a", action=ActionType.CREATE, target_type="x", target_id="1")
        trail.record(actor="b", action=ActionType.MODIFY, target_type="x", target_id="1")
        trail.record(actor="c", action=ActionType.APPROVE, target_type="x", target_id="1")
        assert trail.count == 3
        # entries are ordered
        assert trail.entries[0].actor == "a"
        assert trail.entries[2].actor == "c"

    def test_hash_chain_genesis(self):
        trail = AuditTrail()
        e = trail.record(actor="a", action=ActionType.LOGIN, target_type="user", target_id="u1")
        assert e.previous_hash == "genesis"
        assert len(e.entry_hash) == 64  # SHA-256 hex

    def test_hash_chain_links(self):
        trail = AuditTrail()
        e1 = trail.record(actor="a", action=ActionType.CREATE, target_type="x", target_id="1")
        e2 = trail.record(actor="b", action=ActionType.MODIFY, target_type="x", target_id="1")
        assert e2.previous_hash == e1.entry_hash

    def test_verify_chain_valid(self):
        trail = AuditTrail()
        for i in range(10):
            trail.record(actor=f"user-{i}", action=ActionType.CREATE, target_type="item", target_id=str(i))
        assert trail.verify_chain() is True

    def test_verify_chain_tampered(self):
        trail = AuditTrail()
        trail.record(actor="a", action=ActionType.CREATE, target_type="x", target_id="1")
        trail.record(actor="b", action=ActionType.MODIFY, target_type="x", target_id="1")
        # tamper: forcibly modify an entry's hash
        trail._entries[0] = trail._entries[0].__class__(
            id=trail._entries[0].id,
            timestamp=trail._entries[0].timestamp,
            actor="TAMPERED",
            action=trail._entries[0].action,
            target_type=trail._entries[0].target_type,
            target_id=trail._entries[0].target_id,
            details=trail._entries[0].details,
            data_sources=trail._entries[0].data_sources,
            previous_hash=trail._entries[0].previous_hash,
            entry_hash=trail._entries[0].entry_hash,
        )
        assert trail.verify_chain() is False

    def test_query_by_target(self):
        trail = AuditTrail()
        trail.record(actor="a", action=ActionType.CREATE, target_type="portfolio", target_id="p1")
        trail.record(actor="b", action=ActionType.CREATE, target_type="portfolio", target_id="p2")
        trail.record(actor="c", action=ActionType.MODIFY, target_type="portfolio", target_id="p1")
        results = trail.query(target_id="p1")
        assert len(results) == 2

    def test_query_by_actor(self):
        trail = AuditTrail()
        trail.record(actor="alice", action=ActionType.CREATE, target_type="x", target_id="1")
        trail.record(actor="bob", action=ActionType.MODIFY, target_type="x", target_id="1")
        results = trail.query(actor="alice")
        assert len(results) == 1

    def test_separation_of_duty_violation(self):
        trail = AuditTrail()
        v = trail.separation_of_duty_violation(creator="alice", approver="alice", executor="bob")
        assert v is not None
        assert "violated" in v

    def test_separation_of_duty_clean(self):
        trail = AuditTrail()
        v = trail.separation_of_duty_violation(creator="alice", approver="bob", executor="charlie")
        assert v is None

    def test_data_sources_recorded(self):
        trail = AuditTrail()
        e = trail.record(
            actor="a", action=ActionType.DATA_IMPORT, target_type="dataset",
            target_id="d1", data_sources=["IMF", "World Bank"]
        )
        assert e.data_sources == ["IMF", "World Bank"]


# ── Approval Workflow ────────────────────────────────────────────────

class TestApprovalWorkflow:
    def _make_workflow(self):
        return ApprovalWorkflow(
            levels=[ApprovalLevel.ANALYST, ApprovalLevel.MANAGER],
            expiry_hours=72,
        )

    def test_create_and_submit(self):
        wf = self._make_workflow()
        p = wf.create_proposal(proposal_id="prop-1", title="Buy AAPL", description="Increase to 15%", created_by="alice")
        assert p.status == ProposalStatus.DRAFT
        p = wf.submit("prop-1", submitted_by="alice")
        assert p.status == ProposalStatus.PENDING

    def test_cannot_submit_twice(self):
        wf = self._make_workflow()
        wf.create_proposal(proposal_id="prop-1", title="X", description="Y", created_by="alice")
        wf.submit("prop-1", submitted_by="alice")
        with pytest.raises(ValueError, match="Cannot submit"):
            wf.submit("prop-1", submitted_by="alice")

    def test_approve_separation_of_duties(self):
        wf = self._make_workflow()
        wf.create_proposal(proposal_id="prop-1", title="X", description="Y", created_by="alice")
        wf.submit("prop-1", submitted_by="alice")
        with pytest.raises(PermissionError, match="Separation of duties"):
            wf.approve("prop-1", approver="alice", level=ApprovalLevel.ANALYST)

    def test_full_approval_flow(self):
        wf = self._make_workflow()
        wf.create_proposal(proposal_id="prop-1", title="X", description="Y", created_by="alice")
        wf.submit("prop-1", submitted_by="alice")
        wf.approve("prop-1", approver="bob", level=ApprovalLevel.ANALYST)
        wf.approve("prop-1", approver="charlie", level=ApprovalLevel.MANAGER)
        p = wf.get("prop-1")
        assert p.status == ProposalStatus.APPROVED

    def test_reject(self):
        wf = self._make_workflow()
        wf.create_proposal(proposal_id="prop-1", title="X", description="Y", created_by="alice")
        wf.submit("prop-1", submitted_by="alice")
        wf.reject("prop-1", rejector="bob", level=ApprovalLevel.ANALYST, reason="Too aggressive")
        p = wf.get("prop-1")
        assert p.status == ProposalStatus.REJECTED

    def test_execute_separation(self):
        wf = self._make_workflow()
        wf.create_proposal(proposal_id="prop-1", title="X", description="Y", created_by="alice")
        wf.submit("prop-1", submitted_by="alice")
        wf.approve("prop-1", approver="bob", level=ApprovalLevel.ANALYST)
        wf.approve("prop-1", approver="charlie", level=ApprovalLevel.MANAGER)
        # charlie approved → cannot execute
        with pytest.raises(PermissionError, match="Separation of duties"):
            wf.mark_executed("prop-1", executor="charlie", result={"status": "filled"})
        # bob approved → cannot execute
        with pytest.raises(PermissionError, match="Separation of duties"):
            wf.mark_executed("prop-1", executor="bob", result={"status": "filled"})
        # dave (no role) → can execute
        p = wf.mark_executed("prop-1", executor="dave", result={"status": "filled"})
        assert p.status == ProposalStatus.EXECUTED

    def test_audit_trail_records(self):
        wf = self._make_workflow()
        wf.create_proposal(proposal_id="prop-1", title="X", description="Y", created_by="alice")
        wf.submit("prop-1", submitted_by="alice")
        wf.approve("prop-1", approver="bob", level=ApprovalLevel.ANALYST)
        assert wf.audit.count == 3  # create + submit + approve


# ── Assumption Registry ──────────────────────────────────────────────

class TestAssumptionRegistry:
    def test_register(self):
        reg = AssumptionRegistry()
        a = reg.register(
            assumption_id="a1", category="market", key="risk_free_rate",
            value=0.02, source="US Treasury 10Y", created_by="alice",
        )
        assert a.value == 0.02
        assert a.version == 1

    def test_update_creates_version(self):
        reg = AssumptionRegistry()
        reg.register(assumption_id="a1", category="market", key="risk_free_rate", value=0.02, source="Treasury")
        new = reg.update("a1", new_value=0.025, updated_by="bob", rationale="Rates rose")
        assert new.version == 2
        assert new.value == 0.025
        old = reg.get("a1")
        assert old.superseded_by is not None
        assert len(reg.list_active()) == 1

    def test_create_set(self):
        reg = AssumptionRegistry()
        reg.register(assumption_id="a1", category="market", key="rf", value=0.02)
        reg.register(assumption_id="a2", category="model", key="lookback", value=252)
        s = reg.create_set(set_id="s1", name="Standard Model Run", assumption_ids=["a1", "a2"])
        assert len(s.assumptions) == 2

    def test_link_to_decision(self):
        reg = AssumptionRegistry()
        reg.register(assumption_id="a1", category="market", key="rf", value=0.02)
        reg.link_to_decision("a1", "decision-1")
        reg.link_to_decision("a1", "decision-2")
        affected = reg.get_affected_decisions("a1")
        assert affected == ["decision-1", "decision-2"]

    def test_detect_conflicts(self):
        reg = AssumptionRegistry()
        reg.register(assumption_id="a1", category="market", key="rf", value=0.02)
        reg.register(assumption_id="a2", category="market", key="rf", value=0.05)
        conflicts = reg.detect_conflicts(["a1", "a2"])
        assert len(conflicts) == 1
        assert "Conflict" in conflicts[0]

    def test_detect_low_confidence(self):
        reg = AssumptionRegistry()
        reg.register(assumption_id="a1", category="data", key="gdp_growth", value=0.03, confidence=0.2)
        conflicts = reg.detect_conflicts(["a1"])
        assert any("Low confidence" in c for c in conflicts)

    def test_export_set(self):
        reg = AssumptionRegistry()
        reg.register(assumption_id="a1", category="market", key="rf", value=0.02, source="Treasury")
        reg.create_set(set_id="s1", name="Test", assumption_ids=["a1"])
        exported = reg.export_set("s1")
        assert exported["name"] == "Test"
        assert len(exported["assumptions"]) == 1


# ── Explainability Engine ────────────────────────────────────────────

class TestExplainabilityEngine:
    def _make_engine(self):
        return ExplainabilityEngine()

    def test_build_valid(self):
        eng = self._make_engine()
        rec = eng.build(
            rec_id="r1", title="Buy AAPL", action_type="buy", target="AAPL",
            confidence=0.75,
            confidence_basis="Backtest 75% win rate",
            assumptions=[AssumptionRef(key="rf", value=0.02, source="Treasury", confidence=0.9)],
            alternatives=[Alternative(description="Hold current")],
            risks=[Risk(description="Model error", severity="medium")],
            data_sources=[DataSource(name="Yahoo", type="market_data", quality_score=0.85, staleness_hours=1)],
            ai_interpretation="Model suggests buying",
            counterargument="Could also hold",
        )
        assert rec.confidence == 0.75
        errors = eng.validate(rec)
        assert len(errors) == 0

    def test_build_fails_without_alternatives(self):
        eng = ExplainabilityEngine(require_alternatives=True)
        with pytest.raises(ValueError, match="alternative"):
            eng.build(
                rec_id="r1", title="X", action_type="buy", target="AAPL",
                confidence=0.7, confidence_basis="basis",
                assumptions=[AssumptionRef(key="k", value=1, source="s", confidence=0.9)],
                risks=[Risk(description="r", severity="low")],
                data_sources=[DataSource(name="n", type="market_data", quality_score=0.8, staleness_hours=1)],
                ai_interpretation="text", counterargument="counter",
            )

    def test_build_fails_without_risks(self):
        eng = self._make_engine()
        with pytest.raises(ValueError, match="risk"):
            eng.build(
                rec_id="r1", title="X", action_type="buy", target="AAPL",
                confidence=0.7, confidence_basis="basis",
                assumptions=[AssumptionRef(key="k", value=1, source="s", confidence=0.9)],
                alternatives=[Alternative(description="alt")],
                data_sources=[DataSource(name="n", type="market_data", quality_score=0.8, staleness_hours=1)],
                ai_interpretation="text", counterargument="counter",
            )

    def test_build_fails_without_counterargument(self):
        eng = self._make_engine()
        with pytest.raises(ValueError, match="(?i)counterargument"):
            eng.build(
                rec_id="r1", title="X", action_type="buy", target="AAPL",
                confidence=0.7, confidence_basis="basis",
                assumptions=[AssumptionRef(key="k", value=1, source="s", confidence=0.9)],
                alternatives=[Alternative(description="alt")],
                risks=[Risk(description="r", severity="low")],
                data_sources=[DataSource(name="n", type="market_data", quality_score=0.8, staleness_hours=1)],
                ai_interpretation="text",
            )

    def test_from_quantive_output(self):
        eng = self._make_engine()
        rec = eng.from_quantive_output(
            ticker="AAPL", weight=0.15, prev_weight=0.10,
            expected_return=0.08, risk=0.15, confidence=0.72,
        )
        assert rec.action_type == "buy"
        assert rec.target == "AAPL"
        errors = eng.validate(rec)
        assert len(errors) == 0

    def test_from_quantive_output_hold(self):
        eng = self._make_engine()
        rec = eng.from_quantive_output(
            ticker="MSFT", weight=0.10, prev_weight=0.10,
            expected_return=0.06, risk=0.12, confidence=0.65,
        )
        assert rec.action_type == "hold"

    def test_to_report_shape(self):
        eng = self._make_engine()
        rec = eng.from_quantive_output(
            ticker="GOOG", weight=0.08, prev_weight=0.12,
            expected_return=0.10, risk=0.20, confidence=0.55,
        )
        report = rec.to_report()
        assert "recommendation" in report
        assert "confidence" in report
        assert "assumptions" in report
        assert "alternatives" in report
        assert "risks" in report
        assert "data_sources" in report
        assert "model" in report
        assert "ai_interpretation" in report
        assert "counterargument" in report
        # AI disclaimer is present
        assert "interpretation" in report["ai_interpretation"]["disclaimer"].lower()

    def test_validate_catches_missing_ai_interpretation(self):
        from quantive.trust.explainability import ExplainableRecommendation
        eng = self._make_engine()
        rec = ExplainableRecommendation(
            id="r1", title="X", action_type="buy", target="T",
            confidence=0.8, confidence_basis="basis",
            assumptions=[AssumptionRef(key="k", value=1, source="s", confidence=0.9)],
            alternatives=[Alternative(description="alt")],
            risks=[Risk(description="r", severity="low")],
            data_sources=[DataSource(name="n", type="market_data", quality_score=0.8, staleness_hours=1)],
            ai_interpretation="", counterargument="counter",
        )
        errors = eng.validate(rec)
        assert any("AI interpretation" in e for e in errors)
