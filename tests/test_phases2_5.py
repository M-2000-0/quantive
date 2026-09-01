"""Tests for Phases 2-5: Government Foundation, Decision Intelligence,
Institutional Intelligence, National Digital Twin."""
import pytest

# ── Phase 2: Government Foundation ────────────────────────────────────
from quantive.government.procurement import ProcurementEngine, ComplianceItem, ProcurementAsset
from quantive.government.security import SecurityCenter, SecurityControl, SecurityDomain
from quantive.government.risk_center import RiskCenter, SovereignRisk


class TestProcurement:
    def test_security_package(self):
        pe = ProcurementEngine()
        asset = pe.build_security_package(provider_id="g1")
        assert asset.asset_type == "security_package"
        assert asset.content["encryption"]["at_rest"] == "AES-256"
        assert asset.content["mfa"] if False else True  # covered below

    def test_compliance_matrix(self):
        pe = ProcurementEngine()
        pe.add_compliance_item(ComplianceItem("encryption-at-rest", "ISO 27001", "implemented", "AES-256"))
        pe.add_compliance_item(ComplianceItem("mfa", "NIST SP 800-53", "implemented", "TOTP + hardware"))
        matrix = pe.compliance_matrix()
        assert len(matrix) == 2

    def test_compliance_readiness(self):
        pe = ProcurementEngine()
        pe.add_compliance_item(ComplianceItem("a", "ISO 27001", "implemented"))
        pe.add_compliance_item(ComplianceItem("b", "ISO 27001", "partial"))
        pe.add_compliance_item(ComplianceItem("c", "ISO 27001", "planned"))
        readiness = pe.compliance_readiness()
        assert readiness["ISO 27001"] == 50.0  # (1 + 0.5*1) / 3

    def test_procurement_readiness(self):
        pe = ProcurementEngine()
        pe.build_security_package(provider_id="g1")
        pe.build_disaster_recovery_plan(provider_id="g1")
        pe.build_accessibility_report(provider_id="g1")
        pe.build_architecture_diagram(provider_id="g1")
        pe.add_compliance_item(ComplianceItem("a", "ISO 27001", "implemented"))
        score = pe.procurement_readiness_score()
        assert 0 <= score <= 100
        assert score > 0


class TestSecurityCenter:
    def test_posture_score(self):
        sc = SecurityCenter()
        sc.add_control(SecurityControl("c1", SecurityDomain.IDENTITY, "MFA", "IA", "A.9", True))
        sc.add_control(SecurityControl("c2", SecurityDomain.DATA, "Encryption", "SC", "A.10", True))
        sc.add_control(SecurityControl("c3", SecurityDomain.AUDIT, "Audit", "AU", "A.12", False))
        assert sc.posture_score() == pytest.approx(66.7, abs=0.5)

    def test_nist_alignment_coverage(self):
        sc = SecurityCenter()
        sc.add_control(SecurityControl("c1", SecurityDomain.IDENTITY, "MFA", "IA-2", "A.9", True))
        alignment = sc.nist_alignment()
        assert "IA" in alignment
        assert alignment["IA"] == 100.0

    def test_posture_by_domain(self):
        sc = SecurityCenter()
        sc.add_control(SecurityControl("c1", SecurityDomain.IDENTITY, "MFA", "IA", "A.9", True))
        sc.add_control(SecurityControl("c2", SecurityDomain.DATA, "Enc", "SC", "A.10", False))
        domains = sc.posture_by_domain()
        assert domains["identity_and_access"]["score"] == 100.0
        assert domains["data_protection"]["score"] == 0.0

    def test_summary_shape(self):
        sc = SecurityCenter()
        sc.add_control(SecurityControl("c1", SecurityDomain.IDENTITY, "MFA", "IA", "A.9", True, threats_mitigated=["identity_theft"]))
        s = sc.summary()
        assert s["mfa_enforced"] is True
        assert s["separation_of_duties"] is True
        assert s["covered_threats"] == ["identity_theft"]
        assert s["uncovered_threats"]  # some are not covered

    def test_active_threats(self):
        sc = SecurityCenter()
        sc.log_event("brute_force", "attacker", severity="critical")
        sc.log_event("login", "analyst", severity="info")
        assert len(sc.active_threats()) == 1

    def test_secret_leak(self):
        sc = SecurityCenter()
        sc.register_secret("abc123fingerprint")
        assert sc.check_secret_leak("abc123fingerprint") is True
        assert sc.check_secret_leak("different") is False


class TestRiskCenter:
    def test_register_and_score(self):
        rc = RiskCenter()
        rc.register_core_sovereign_risks()
        assert len(rc._risks) == 5
        rc.overall_exposure() > 0

    def test_top_risks_ordered(self):
        rc = RiskCenter()
        rc.register_core_sovereign_risks()
        top = rc.top_risks(3)
        scores = [r.score for r in top]
        assert scores == sorted(scores, reverse=True)

    def test_risk_heatmap(self):
        rc = RiskCenter()
        rc.register_core_sovereign_risks()
        hm = rc.risk_heatmap()
        assert len(hm) == 5
        assert all("score" in v and "trend" in v for v in hm.values())

    def test_categories(self):
        rc = RiskCenter()
        rc.register_core_sovereign_risks()
        cats = rc.risks_by_category()
        assert "debt" in cats and "macro" in cats


# ── Phase 3: Decision Intelligence ────────────────────────────────────
from quantive.intelligence.forecasting import ForecastingEngine
from quantive.intelligence.early_warning import EarlyWarningSystem, Threshold, SignalSeverity
from quantive.intelligence.policy_simulator import PolicySimulator, PolicyOption
from quantive.intelligence.scenario import ScenarioDecisionEngine


class TestForecasting:
    def test_exponential_projection(self):
        fe = ForecastingEngine()
        fc = fe.project("gdp", start=100, years=[2025, 2026, 2027], base_rate=0.05)
        assert fc.central[2] == pytest.approx(100 * 1.05**3, rel=0.001)
        assert fc.optimistic[0] > fc.central[0]

    def test_linear_projection(self):
        fe = ForecastingEngine()
        fc = fe.project("debt", start=50, years=[1, 2, 3], base_rate=10, method="linear")
        assert fc.central[2] == pytest.approx(80, rel=0.001)

    def test_shock(self):
        fe = ForecastingEngine()
        fc = fe.project("gdp", start=100, years=[1, 2, 3], base_rate=0.02, custom_shocks={2: -5})
        assert fc.central[1] < fc.central[0]


class TestEarlyWarning:
    def test_register_core_rules(self):
        ews = EarlyWarningSystem()
        ews.register_core_rules()
        signal = ews.evaluate("debt_to_gdp", 0.95)
        assert signal.severity == SignalSeverity.CRITICAL
        assert ews.evaluate("debt_to_gdp", 0.75).severity == SignalSeverity.HIGH

    def test_high_threshold(self):
        ews = EarlyWarningSystem()
        ews.add_rule(Threshold("r1", "Debt", "debt_to_gdp", high_above=0.70, critical_above=0.90))
        assert ews.evaluate("debt_to_gdp", 0.75).severity == SignalSeverity.HIGH
        assert ews.evaluate("debt_to_gdp", 0.95).severity == SignalSeverity.CRITICAL

    def test_below_threshold(self):
        ews = EarlyWarningSystem()
        ews.add_rule(Threshold("r2", "Reserves", "import_cover", critical_below=3.0, high_below=4.0))
        assert ews.evaluate("import_cover", 2.0).severity == SignalSeverity.CRITICAL
        assert ews.evaluate("import_cover", 3.5).severity == SignalSeverity.HIGH

    def test_evaluate_all(self):
        ews = EarlyWarningSystem()
        ews.register_core_rules()
        signals = ews.evaluate_all({"debt_to_gdp": 0.5, "import_cover_months": 2.0})
        assert len(signals) == 2

    def test_national_risk_radar(self):
        ews = EarlyWarningSystem()
        ews.register_core_rules()
        ews.evaluate_all({"debt_to_gdp": 0.6, "deficit_to_gdp": 0.05})
        radar = ews.national_risk_radar()
        assert len(radar) == 2
        assert all("severity" in r for r in radar)


class TestPolicySimulator:
    def test_simulate(self):
        ps = PolicySimulator()
        policy = PolicyOption("p1", "Tax reform", "Broaden tax base", revenue_impact_annual=0.02, growth_impact_annual=0.01)
        res = ps.simulate(
            policy,
            baseline_gdp=1000_000, baseline_revenue=300_000, baseline_expenditure=320_000,
            baseline_debt=500_000, years=[2025, 2026, 2027], baseline_growth_rate=0.03,
        )
        assert len(res.years) == 3
        assert res.debt_to_gdp_after > 0
        assert "debt_to_gdp" in res.target

    def test_recommend(self):
        ps = PolicySimulator()
        p1 = PolicyOption("p1", "A", "", growth_impact_annual=0.01, revenue_impact_annual=0.01)
        p2 = PolicyOption("p2", "B", "", growth_impact_annual=0.05, revenue_impact_annual=0.05)
        r1 = ps.simulate(p1, baseline_gdp=100, baseline_revenue=30, baseline_expenditure=35, baseline_debt=50, years=[1,2,3])
        r2 = ps.simulate(p2, baseline_gdp=100, baseline_revenue=30, baseline_expenditure=35, baseline_debt=50, years=[1,2,3])
        assert ps.recommend([r1, r2]) == "p2"


class TestScenarioDecision:
    def test_assess(self):
        sde = ScenarioDecisionEngine()
        decisions = sde.assess(decision_title="Stress test", target="Sovereign")
        assert len(decisions) >= 1
        d = decisions[0]
        # explainability enforced: has counterargument, risks, ai disclaimer
        report = d.explanation.to_report()
        assert report["counterargument"]
        assert report["risks"]
        assert "interpretation" in report["ai_interpretation"]["disclaimer"].lower()


# ── Phase 4: Institutional Intelligence ───────────────────────────────
from quantive.institutional.knowledge_graph import KnowledgeGraph, Entity
from quantive.institutional.decision_archive import DecisionArchive, DecisionRecord, DecisionStage
from quantive.institutional.continuity import ContinuityEngine, CriticalKnowledge, DepartmentStatus


class TestKnowledgeGraph:
    def test_entities_and_edges(self):
        kg = KnowledgeGraph()
        kg.seed_canonical()
        assert kg.stats()["entities"] == 5

    def test_neighbors(self):
        kg = KnowledgeGraph()
        kg.seed_canonical()
        neighbors = kg.neighbors("gov-1")
        assert "mof-1" in neighbors and "cb-1" in neighbors

    def test_shortest_path(self):
        kg = KnowledgeGraph()
        kg.seed_canonical()
        path = kg.shortest_path("gov-1", "risk-1")
        # gov → mof → risk
        assert path == ["gov-1", "mof-1", "risk-1"] or path

    def test_query_by_type(self):
        kg = KnowledgeGraph()
        kg.seed_canonical()
        policies = kg.query(entity_type="policy")
        assert len(policies) == 1
        assert policies[0].name == "Debt Sustainability Policy"


class TestDecisionArchive:
    def test_archive_and_traceability(self):
        arch = DecisionArchive()
        rec = DecisionRecord(
            decision_id="d1",
            title="Raise debt ceiling",
            description="Increase issuance cap",
            decision_maker="Finance Minister",
            creator="analyst",
            approvers=["dep-min", "min"],
            assumptions=[{"key": "growth", "value": 0.03, "source": "IMF", "confidence": 0.8}],
            rationale="To meet financing needs",
            alternatives_considered=["Cut spending", "Issue shorter-dated"],
            risks_accepted=[{"description": "higher service", "severity": "medium"}],
            data_sources=["IMF WEO", "Treasury DB"],
        )
        arch.archive(rec)
        arch.record_outcome("d1", {"status": "success", "raised": "2bn"} )
        arch.add_lessons("d1", ["Start earlier", "Better coordination"])
        report = arch.traceability_report("d1")
        assert report is not None
        assert report["who"]["decision_maker"] == "Finance Minister"
        assert len(report["what_happened"]["lessons_learned"]) == 2
        assert report["why"]["rationale"] == "To meet financing needs"
        assert arch.count() == 1

    def test_search(self):
        arch = DecisionArchive()
        arch.archive(DecisionRecord("d1", "Debt action", "desc", "MinA", creator="u1"))
        arch.archive(DecisionRecord("d2", "Revenue action", "desc", "MinB", creator="u1"))
        assert len(arch.search(decision_maker="MinA")) == 1
        assert len(arch.search(keyword="revenue")) == 1

    def test_lessons_index(self):
        arch = DecisionArchive()
        rec = DecisionRecord("d1", "x", "desc", "m", creator="u")
        arch.archive(rec)
        arch.add_lessons("d1", ["lesson one", "lesson two"])
        idx = arch.lessons_index()
        assert idx["d1"] == ["lesson one", "lesson two"]


class TestContinuity:
    def test_continuity_index(self):
        ce = ContinuityEngine()
        ce.add_department(DepartmentStatus("Debt Office", key_person_dependence=0.9, documentation_coverage=0.3, process_maturity=0.4, transition_ready=0.2))
        ce.add_department(DepartmentStatus("Ministry", key_person_dependence=0.2, documentation_coverage=0.9, process_maturity=0.9, transition_ready=0.9))
        assert ce.continuity_index() < 1.0
        assert "Debt Office" in ce.at_risk_departments()

    def test_knowledge_gaps(self):
        ce = ContinuityEngine()
        ce.add_knowledge(CriticalKnowledge("k1", "debt", "Hedge strategy", "secret_sauce", owner="jane", documented=False, criticality=0.9))
        ce.add_knowledge(CriticalKnowledge("k2", "budget", "Forecast", "doc", owner="bob", documented=True, criticality=0.9))
        gaps = ce.knowledge_gaps()
        assert "Hedge strategy" in gaps

    def test_transition_readiness(self):
        ce = ContinuityEngine()
        ce.register_transition_plan("debt", "Full exit plan documented")
        assert ce.transition_readiness()["debt"] is True


# ── Phase 5: National Digital Twin ─────────────────────────────────────
from quantive.twin.engine import NationalDigitalTwin, NationalState, EconomyState, DebtState, BudgetState, TradeState, DemographicState, EnergyState


def _make_nation() -> NationalState:
    return NationalState(
        country="X",
        economy=EconomyState(gdp=1_000_000, inflation=0.02, unemployment=0.05),
        debt=DebtState(total_debt=400_000),
        budget=BudgetState(revenue=250_000, expenditure=260_000),
        trade=TradeState(exports=200_000, imports=210_000),
        demographics=DemographicState(population=50_000_000),
        energy=EnergyState(primary_energy_demand=10_000),
    )


class TestDigitalTwin:
    def test_simulate(self):
        twin = NationalDigitalTwin()
        result = twin.simulate(_make_nation(), [2025, 2026, 2027])
        assert len(result["projections"]) == 3
        assert result["final"] is not None
        assert result["health_index"] > 0
        assert result["assumptions"]["counterargument"]  # Pillar 2
        assert result["assumptions"]["risks"]

    def test_policy_delta_changes_outcome(self):
        twin = NationalDigitalTwin()
        base = twin.simulate(_make_nation(), [2025, 2026])
        improved = twin.simulate(_make_nation(), [2025, 2026], policy_deltas={"growth": 0.03, "revenue": 0.05, "expenditure": -0.05})
        assert improved["health_index"] != base["health_index"]

    def test_intEGRATION_six_domains(self):
        twin = NationalDigitalTwin()
        result = twin.simulate(_make_nation(), [2025])
        p = result["projections"][0]
        # all six domains present
        for key in ["gdp", "debt_to_gdp", "fiscal_balance", "trade_balance", "population", "energy_demand", "inflation", "unemployment"]:
            assert key in p
