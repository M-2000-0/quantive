"""Comprehensive seed script — populates ALL demo data for investor/government demo.

Run: python -m scripts.seed_all
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib
import uuid

from sqlalchemy import text

from app.database import SessionLocal, engine, Base
from app.models import (
    Organization, User, Portfolio, DebtInstrument, DebtInstrumentType,
)
from app.models.pfm import (
    BudgetEntry, RevenueRecord, ExpenditureRecord, AuditFinding,
    FinancialStatement, IFMISConnection,
)
from app.models.ai_governance import (
    ModelCard, AlgorithmEntry, CrisisScenario, BacktestResult,
    BiasReport, DecisionRecord, DataLineageRecord, ExplainabilityReport,
)
from app.models.exchange_integration import (
    ExchangeConnection, ComplianceRule, ComplianceEvent, CounterpartyRiskScore,
    TradeOrder, RiskAllocation, EthicalFirewall, RegulatoryReport,
    MarketDataFeed, CCPClearingMember, SmartContractTemplate,
    InstitutionalCapacityAssessment, AlgorithmAuditTrail, ExchangeConnectorTemplate,
)
from app.models.broker_integration import (
    ClientKYC, ClientOnboarding, TransactionRecord, TransactionMonitoringRule,
    BrokerRegistration, FeeSchedule, BestExecutionRecord,
)
from app.models.regulatory_compliance import (
    RegulatoryCertification, CertificationType, CertificationStatus,
    AlgorithmicImpactAssessment, ImpactSeverity, ValidationStatus,
    StressTest, StressTestType, StressTestResultStatus,
    CrossBorderSettlement, SettlementStatus, SettlementNetwork,
    ExplainabilityDisclosure, DisclosureType, DisclosureStatus,
)
from app.models.exchange_due_diligence import (
    PreTradeControl, ControlType, ControlStatus,
    SimulationEnvironment, SimulationStatus,
    MarketSurveillance, SurveillanceAlertType, SurveillanceSeverity, SurveillanceStatus,
    ProofOfReserve, ReserveChain, ReserveStatus,
    DecisionLog, DecisionType,
)
from app.models.cybersecurity_privacy import (
    RegulatoryMonitoring, MonitoringStatus, AlertSeverity,
    CybersecurityControl, SecurityControlType, SecurityStatus,
    DataPrivacyCompliance, PrivacyFramework, DataClassification,
    InteroperabilityStandard, InteroperabilityFramework, ComplianceStandardStatus,
)
from app.models.validation_vendor import (
    IndependentValidation, ValidationStatus as ValStatus, ValidationType, SignOffRole,
    VendorRiskAssessment, VendorCriticality, VendorStatus, VendorCategory,
)


def now():
    return datetime.now(timezone.utc)


def days_ago(n):
    return now() - timedelta(days=n)


def future_days(n):
    return now() + timedelta(days=n)


def months_ago(n):
    return now() - timedelta(days=n * 30)


def gen_id():
    return str(uuid.uuid4())


def sha256_hash(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


# ── Organization & User ───────────────────────────────────────────────

def seed_org_and_user(session):
    print("[1/8] Seeding organization and user...")

    org_id = gen_id()
    org = Organization(id=org_id, name="Quantive Demo Organization")
    session.add(org)

    user_id = gen_id()
    user = User(
        id=user_id,
        email="demo@quantive.com",
        password_hash=sha256_hash("demo_password"),
        name="Demo Admin",
        role="admin",
        is_active=True,
        email_verified=True,
        org_id=org_id,
    )
    session.add(user)
    session.flush()  # Flush to generate IDs before creating portfolio

    portfolio_id = gen_id()
    portfolio = Portfolio(
        id=portfolio_id,
        name="Sovereign Debt Portfolio",
        description="Demo sovereign debt portfolio for investor presentation",
        org_id=org_id,
        created_by=user_id,
    )
    session.add(portfolio)

    # Add debt instruments
    instruments = [
        ("US Treasury 10Y", DebtInstrumentType.TREASURY_BOND, "USD", 50_000_000, 4.25, "2034-06-15", "2024-06-15"),
        ("US Treasury 5Y", DebtInstrumentType.T_BILL, "USD", 30_000_000, 3.85, "2029-06-15", "2024-06-15"),
        ("UK Gilts 15Y", DebtInstrumentType.SOVEREIGN_BOND, "GBP", 25_000_000, 4.50, "2039-03-22", "2024-03-22"),
        ("Japan Govt 20Y", DebtInstrumentType.SOVEREIGN_BOND, "JPY", 5_000_000_000, 1.10, "2044-09-20", "2024-09-20"),
        ("IMF Concessional", DebtInstrumentType.CONCESSIONAL_LOAN, "SDR", 15_000_000, 1.00, "2039-12-31", "2024-01-01"),
        ("Eurobond 2030", DebtInstrumentType.EUROBOND, "USD", 20_000_000, 5.75, "2030-04-15", "2024-04-15"),
        ("Domestic Bond 7Y", DebtInstrumentType.DOMESTIC_BOND, "USD", 40_000_000, 4.80, "2031-11-01", "2024-11-01"),
        ("FRN 3M", DebtInstrumentType.FLOATING_RATE_NOTE, "USD", 10_000_000, 5.25, "2027-06-15", "2024-06-15"),
    ]

    for name, itype, ccy, principal, coupon, mat, iss in instruments:
        inst = DebtInstrument(
            id=gen_id(), portfolio_id=portfolio_id, name=name,
            instrument_type=itype, currency=ccy, principal_outstanding=float(principal),
            coupon_rate=float(coupon), maturity_date=mat, issue_date=iss,
        )
        session.add(inst)

    session.commit()
    print(f"  Created org {org_id}, user {user_id}, portfolio {portfolio_id}, {len(instruments)} instruments")
    return org_id, user_id, portfolio_id


# ── PFM Data ──────────────────────────────────────────────────────────

def seed_pfm(session, org_id):
    print("[2/8] Seeding PFM data...")

    from app.models.pfm import BudgetStatus, RevenueType, ExpenditureType, AuditType, AuditSeverity, StatementType

    # Budget entries (FY2024)
    budget_items = [
        ("01-01-001", "Revenue — Personal Income Tax", "Ministry of Finance", "revenue", 180_000_000, 185_000_000, 185_000_000),
        ("01-01-002", "Revenue — Corporate Tax", "Ministry of Finance", "revenue", 95_000_000, 92_000_000, 92_000_000),
        ("01-01-003", "Revenue — VAT", "Ministry of Finance", "revenue", 120_000_000, 125_000_000, 125_000_000),
        ("01-02-001", "Revenue — Customs Duties", "Customs Authority", "revenue", 35_000_000, 38_000_000, 38_000_000),
        ("01-02-002", "Revenue — Mining Royalties", "Ministry of Mines", "revenue", 22_000_000, 18_000_000, 18_000_000),
        ("02-01-001", "Expenditure — Education", "Ministry of Education", "recurrent", 95_000_000, 98_000_000, 96_000_000),
        ("02-01-002", "Expenditure — Healthcare", "Ministry of Health", "recurrent", 70_000_000, 72_000_000, 70_500_000),
        ("02-01-003", "Expenditure — Defense", "Ministry of Defense", "recurrent", 45_000_000, 44_000_000, 44_000_000),
        ("02-02-001", "Expenditure — Infrastructure", "Ministry of Works", "capital", 60_000_000, 55_000_000, 48_000_000),
        ("02-03-001", "Expenditure — Debt Service", "Debt Management Office", "servicing", 42_000_000, 45_000_000, 45_000_000),
        ("02-01-004", "Expenditure — Social Protection", "Ministry of Social Affairs", "recurrent", 30_000_000, 32_000_000, 31_000_000),
        ("02-01-005", "Expenditure — Public Order", "Ministry of Interior", "recurrent", 25_000_000, 24_000_000, 24_000_000),
    ]

    for code, prog, dept, cat, proposed, approved, executed in budget_items:
        entry = BudgetEntry(
            id=gen_id(), org_id=org_id,
            fiscal_year=2024, budget_code=code,
            program_name=prog, department=dept,
            budget_category=cat,
            proposed_amount=float(proposed),
            approved_amount=float(approved),
            executed_amount=float(executed),
            status=BudgetStatus.EXECUTING,
        )
        session.add(entry)

    # Revenue records (monthly)
    months = ["M01", "M02", "M03", "M04", "M05", "M06"]
    rev_sources = [
        ("Personal Income Tax", RevenueType.TAX, 15_000_000, 15_400_000),
        ("Corporate Tax", RevenueType.TAX, 7_900_000, 7_600_000),
        ("VAT", RevenueType.TAX, 10_000_000, 10_400_000),
        ("Customs Duties", RevenueType.CUSTOMS, 2_900_000, 3_100_000),
    ]

    for source, rtype, target, actual in rev_sources:
        for i, month in enumerate(months):
            rec = RevenueRecord(
                id=gen_id(), org_id=org_id,
                fiscal_year=2024, fiscal_period=month,
                revenue_type=rtype, revenue_source=source,
                target_amount=float(target * (1 + i * 0.01)),
                collected_amount=float(actual * (1 + i * 0.012)),
                collection_rate=round(actual / target * 100, 1),
            )
            session.add(rec)

    # Expenditure records
    exp_data = [
        ("Ministry of Education", ExpenditureType.PERSONNEL, 8_000_000, 8_200_000),
        ("Ministry of Health", ExpenditureType.GOODS_SERVICES, 5_800_000, 6_000_000),
        ("Ministry of Defense", ExpenditureType.PERSONNEL, 3_750_000, 3_600_000),
        ("Ministry of Works", ExpenditureType.CAPITAL, 5_000_000, 4_500_000),
        ("Debt Management Office", ExpenditureType.DEBT_SERVICE, 3_500_000, 3_750_000),
    ]

    for dept, etype, budgeted, actual in exp_data:
        for i, month in enumerate(months):
            rec = ExpenditureRecord(
                id=gen_id(), org_id=org_id,
                fiscal_year=2024, fiscal_period=month,
                expenditure_type=etype,
                description=f"{dept} — {month} FY2024",
                budgeted_amount=float(budgeted * (1 + i * 0.005)),
                committed_amount=float(actual * 0.1),
                actual_amount=float(actual * (1 + i * 0.008)),
            )
            session.add(rec)

    # Audit findings
    findings = [
        (AuditType.COMPLIANCE, "high", "Irregular procurement in infrastructure project", "Ministry of Works",
         "Open", "Internal Audit Division", "AF-2024-001"),
        (AuditType.EXTERNAL, "medium", "Revenue leakage in customs collection", "Customs Authority",
         "Remediation", "Supreme Audit Office", "AF-2024-002"),
        (AuditType.INTERNAL, "low", "Late submission of financial reports", "Ministry of Education",
         "Closed", "Internal Audit Division", "AF-2024-003"),
        (AuditType.COMPLIANCE, "critical", "Unauthorized expenditure exceeding budget", "Ministry of Health",
         "Escalated", "External Auditor General", "AF-2024-004"),
        (AuditType.PERFORMANCE, "medium", "Weak internal controls in payroll", "Civil Service Commission",
         "Open", "Internal Audit Division", "AF-2024-005"),
        (AuditType.COMPLIANCE, "high", "Non-compliance with PFM Act", "Debt Management Office",
         "Remediation", "Supreme Audit Office", "AF-2024-006"),
    ]

    for atype, sev, desc, entity, status, auditor, ref in findings:
        finding = AuditFinding(
            id=gen_id(), org_id=org_id,
            audit_type=atype, audit_date=days_ago(30),
            auditor_name=auditor, audit_reference=ref,
            title=desc, description=desc,
            severity=sev, financial_impact=5_000_000 if sev in ("critical", "high") else 500_000,
            recommendation="Implement corrective action plan",
        )
        session.add(finding)

    # Financial statements
    for stmt_type, period in [
        (StatementType.ANNUAL, 2024),
        (StatementType.QUARTERLY, 2024),
    ]:
        stmt = FinancialStatement(
            id=gen_id(), org_id=org_id,
            statement_type=stmt_type, fiscal_year=period,
            period_end_date=now(),
            total_assets=250_000_000,
            total_liabilities=180_000_000,
            net_assets=70_000_000,
            total_revenue=452_000_000,
            total_expenditure=392_000_000,
            fiscal_surplus_deficit=60_000_000,
            operating_cash_flow=65_000_000,
            investing_cash_flow=-25_000_000,
            financing_cash_flow=-15_000_000,
        )
        session.add(stmt)

    # IFMIS connection
    ifmis = IFMISConnection(
        id=gen_id(), org_id=org_id,
        system_name="Oracle IFMIS v12.2",
        system_type="ifmis",
        connection_url="https://ifmis.demo.gov",
        api_endpoint="https://ifmis.demo.gov/api/v2",
        last_sync_date=days_ago(1),
        sync_status="completed",
        records_synced=12500,
        data_format="json",
        sync_frequency="daily",
        is_active=True,
    )
    session.add(ifmis)

    session.commit()
    print(f"  Created {len(budget_items)} budget entries, {len(rev_sources)*len(months)} revenue records, {len(exp_data)*len(months)} expenditure records, {len(findings)} audit findings")


# ── AI Governance ─────────────────────────────────────────────────────

def seed_ai_governance(session, org_id):
    print("[3/8] Seeding AI Governance data...")
    from app.models.ai_governance import ModelStatus

    models_data = [
        ("Sovereign Debt Optimizer", "3.2", "optimization", "debt_optimization", "production",
         "Multi-objective optimization of sovereign debt portfolio.",
         "Debt Management Office analysts",
         {"debt_to_gdp": "Current debt-to-GDP ratio", "avg_coupon": "Average coupon rate"},
         "portfolio_allocation", "quantum_annealing", "Dr. Sarah Chen",
         ["Markowitz mean-variance", "Quantum annealing", "Monte Carlo simulation"],
         ["Limited to liquid sovereign bonds"], 99.2),
        ("Early Warning System", "2.1", "ml_classifier", "risk_detection", "production",
         "Predicts sovereign debt distress 12-24 months in advance.",
         "Risk Committee",
         {"gdp_growth": "GDP growth rate", "inflation": "CPI inflation"},
         "risk_score", "gradient_boosting", "Dr. Sarah Chen",
         ["Gradient Boosted Trees", "LSTM neural network"],
         ["May miss novel crisis types"], 94.8),
        ("Market Intelligence", "1.5", "forecasting", "market_analysis", "staging",
         "Real-time market data aggregation and sentiment analysis.",
         "Trading Desk",
         {"news_sentiment": "News sentiment score"},
         "market_signal", "nlp_transformer", "Quantive AI Lab",
         ["NLP sentiment analysis", "Topic modeling"],
         ["English-only training data"], 87.3),
        ("Fraud Detection", "1.0", "anomaly_detection", "compliance", "production",
         "Detects anomalous patterns in government financial transactions.",
         "Compliance Officer",
         {"transaction_amount": "Transaction amount"},
         "anomaly_score", "isolation_forest", "Quantive AI Lab",
         ["Isolation Forest", "Autoencoders"],
         ["May generate false positives"], 96.1),
    ]

    model_card_ids = []
    for name, ver, mtype, cat, status, desc, owner, features, output, method, reviewer, algos, limitations, acc in models_data:
        mc_id = gen_id()
        model_card_ids.append(mc_id)
        card = ModelCard(
            id=mc_id, org_id=org_id,
            model_name=name, model_version=ver,
            model_type=mtype, category=cat,
            status=ModelStatus.DEPLOYED if status == "production" else ModelStatus.VALIDATED,
            intended_use=desc, target_users=owner,
            input_features=features, output_type=output,
            explainability_method=method, owner=owner, reviewer=reviewer,
            approval_date=days_ago(30), next_review_date=days_ago(-90),
            accuracy_metrics={"accuracy": acc},
            known_biases=limitations,
            human_oversight_required=True,
            approval_required_before_deployment=True,
        )
        session.add(card)

    scenarios_data = [
        ("Argentina 2001", "AR", "default", "2001-12", "2005-03",
         148.0, 150.0, 2.1, -3.5, -4.2, 12.0, -11.0, 65.0, 35.0, 13.0, 1500.0),
        ("Greece 2012", "GR", "restructuring", "2010-05", "2015-03",
         170.0, 85.0, 1.5, -9.0, -10.0, 3.0, -6.5, 53.5, 46.5, 5.0, 800.0),
        ("Sri Lanka 2022", "LK", "currency_crisis", "2022-04", "2023-06",
         104.0, 65.0, 0.5, -8.0, -3.5, 70.0, -7.8, 42.0, 58.0, 3.0, 500.0),
        ("US Debt Ceiling 2023", "US", "contagion", "2023-06", "2023-10",
         123.0, 30.0, 15.0, -6.0, -3.0, 3.0, -0.5, 0.0, 100.0, 0.5, 50.0),
        ("Turkey 2018", "TR", "currency_crisis", "2018-06", "2019-03",
         30.0, 45.0, 4.0, -2.0, -3.5, 25.0, -3.0, 18.5, 81.5, 2.0, 450.0),
        ("Ghana 2022", "GH", "default", "2022-12", "2024-06",
         88.0, 55.0, 1.0, -5.0, -2.5, 54.0, -3.5, 30.0, 70.0, 3.0, 350.0),
    ]

    scenario_ids = []
    for name, cc, ctype, start, end, debt, ext, reserves, fiscal, ca, infl, gdp, haircut, recovery, years, contagion in scenarios_data:
        sid = gen_id()
        scenario_ids.append(sid)
        scenario = CrisisScenario(
            id=sid, crisis_name=name, country_code=cc,
            crisis_type=ctype, start_date=start, end_date=end,
            debt_to_gdp_at_crisis=debt, external_debt_ratio=ext,
            reserve_coverage_months=reserves, fiscal_balance_pct_gdp=fiscal,
            current_account_pct_gdp=ca, inflation_pct=infl,
            gdp_growth_pct=gdp, haircuts_pct=haircut,
            recovery_rate_pct=recovery, years_to_resolution=years,
            contagion_spread_bps=contagion,
            description=f"Historical sovereign debt crisis: {name}",
        )
        session.add(scenario)
    session.flush()  # Ensure model cards and scenarios exist before backtest

    for i, sid in enumerate(scenario_ids):
        bt = BacktestResult(
            id=gen_id(), model_card_id=model_card_ids[0],
            scenario_id=sid, org_id=org_id,
            test_date=days_ago(30), lookback_months=24,
            prediction_horizon_months=12,
            prediction="crisis_predicted",
            confidence_score=0.85 + i * 0.02,
            actual_outcome="crisis_occurred", was_correct=True,
            early_warning_months=18 - i,
            top_features=[{"feature": "debt_to_gdp", "importance": 0.35}],
            explanation=f"Model correctly predicted {scenarios_data[i][0]} crisis",
            recommended_action="Reduce exposure and increase hedging",
        )
        session.add(bt)

    bias_reports = [
        ("Jurisdiction Bias", 0.75, 0.82, 0.88, 0.90, "medium",
         ["Underweighting risks in frontier markets"],
         ["Add frontier market training data"]),
        ("Currency Bias", 0.85, 0.90, 0.80, 0.88, "low",
         ["USD-centric training may underestimate EM currency risks"],
         ["Normalize inputs to USD equivalents"]),
        ("Temporal Bias", 0.80, 0.85, 0.78, 0.92, "medium",
         ["Training data skewed toward post-2008 low-rate environment"],
         ["Include pre-2008 high-rate scenarios"]),
    ]

    for title, comp, acc_s, cons, time_s, severity, biases, mitigations in bias_reports:
        bias = BiasReport(
            id=gen_id(), model_card_id=model_card_ids[0], org_id=org_id,
            report_date=days_ago(14), report_type="data_audit",
            completeness_score=comp, accuracy_score=acc_s,
            consistency_score=cons, timeliness_score=time_s,
            severity_level=severity, biases_detected=biases,
            mitigation_actions=mitigations,
            reviewed_by="AI Ethics Board", review_status="approved",
        )
        session.add(bias)

    decisions = [
        ("portfolio_allocation", "Override optimizer for Brazil bonds",
         {"allocation": 0.25}, 0.78, "Reduced from 40% to 25%", "modified", "AI Ethics Board"),
        ("refinancing", "Approve Sri Lanka stress test",
         {"action": "approve"}, 0.94, "Within tolerance", "approved", "Risk Committee"),
        ("issuance_timing", "Reject high-frequency rebalancing",
         {"action": "reject"}, 0.65, "Transaction costs too high", "rejected", "CIO"),
    ]

    for dtype, title, ai_rec, conf, explanation, decision, decider in decisions:
        record = DecisionRecord(
            id=gen_id(), model_card_id=model_card_ids[0], org_id=org_id,
            decision_type=dtype, description=title, urgency="normal",
            ai_recommendation=ai_rec, confidence_score=conf,
            explanation=explanation, human_decision=decision,
            decided_by=decider, decided_at=days_ago(7),
            status=decision,
        )
        session.add(record)

    lineage_data = [
        ("Treasury.gov", "yield_curve_data", "import", "Import daily Treasury yield curve",
         "ai_model_input", 365, 365, 0, 99.5),
        ("ECB", "exchange_rates", "import", "Import EUR/USD exchange rates",
         "ai_model_input", 365, 365, 0, 98.8),
        ("World Bank", "gdp_indicators", "import", "Import quarterly GDP growth",
         "ai_model_input", 40, 40, 0, 97.0),
        ("IMF", "debt_sustainability", "aggregate", "Aggregate debt sustainability indices",
         "dashboard", 190, 190, 0, 95.0),
        ("Manual Upload", "budget_data", "clean", "Clean and validate budget data",
         "ai_model_input", 1500, 1480, 20, 92.0),
    ]

    for sys_name, table, ttype, desc, output, inp, out, drop, score in lineage_data:
        lineage = DataLineageRecord(
            id=gen_id(), org_id=org_id,
            source_system=sys_name, source_table=table,
            transformation_type=ttype, transformation_description=desc,
            output_system=output, input_records=inp, output_records=out,
            records_dropped=drop, quality_score=score,
        )
        session.add(lineage)

    explainability = [
        ("shap", "Why reduce UK Gilts?", "Rising UK inflation +3.2%, GBP depreciation risk.",
         [{"feature": "uk_inflation", "value": 3.2, "contribution": 0.35}], "technical"),
        ("feature_importance", "Why Brazil high-risk?", "Debt/GDP 35%, Political stability 28%.",
         [{"feature": "debt_to_gdp", "value": 78.0, "contribution": 0.35}], "executive"),
    ]

    for rtype, title, summary, features, audience in explainability:
        report = ExplainabilityReport(
            id=gen_id(), model_card_id=model_card_ids[0], org_id=org_id,
            report_type=rtype, title=title, executive_summary=summary,
            feature_contributions=features, target_audience=audience,
        )
        session.add(report)

    session.commit()
    print(f"  Created {len(models_data)} model cards, {len(scenarios_data)} crisis scenarios, {len(bias_reports)} bias reports, {len(decisions)} decisions")


def seed_exchange_integration(session, org_id):
    print("[4/8] Seeding Exchange Integration data...")
    from app.models.exchange_integration import (
        ExchangeType, ConnectionStatus, ExchangeConnectorTemplate,
    )

    # Exchange connections
    exchanges = [
        ("NYSE", ExchangeType.TRADITIONAL, "NYSE-XNYS", "XNYS", "https://api.nyse.com/v2", ConnectionStatus.CONNECTED, "SEC", 95.0),
        ("LSE", ExchangeType.TRADITIONAL, "LSE-XLON", "XLON", "https://api.londonstockexchange.com/v1", ConnectionStatus.CONNECTED, "FCA", 92.0),
        ("Binance", ExchangeType.CRYPTO, "BINANCE", None, "https://api.binance.com/api/v3", ConnectionStatus.CONNECTED, "FCA", 78.0),
        ("CME Group", ExchangeType.TRADITIONAL, "CME-XCME", "XCME", "https://api.cmegroup.com/v1", ConnectionStatus.CONNECTING, "CFTC", 88.0),
        ("JPX", ExchangeType.TRADITIONAL, "JPX-XJPX", "XJPX", "https://www.jpx.co.jp/english/", ConnectionStatus.DISCONNECTED, "JFSA", 0),
    ]

    exchange_ids = []
    for name, etype, eid, mic, api, status, reg, score in exchanges:
        xid = gen_id()
        exchange_ids.append(xid)
        conn = ExchangeConnection(
            id=xid, org_id=org_id,
            exchange_name=name, exchange_type=etype,
            exchange_id=eid, mic_code=mic,
            api_endpoint=api, status=status,
            regulatory_jurisdiction=reg,
            compliance_score=score,
            supports_bonds=True, supports_fx=True,
            supports_equities=(name in ("NYSE", "LSE")),
            supports_derivatives=(name in ("CME Group", "LSE")),
            supports_settlement_t_plus=2 if name != "Binance" else 0,
            daily_trade_limit=100_000_000,
            max_single_trade=50_000_000,
            max_counterparty_exposure=25_000_000,
            last_heartbeat=days_ago(0) if status == ConnectionStatus.CONNECTED else None,
            last_compliance_check=days_ago(1),
        )
        session.add(conn)

    # Compliance rules
    rules_data = [
        ("SEC-15c3-5", "Market Access Rule", "SEC", "US", "risk_control", 10_000_000, True, True),
        ("MiFID-II-BE", "Best Execution", "MiFID II", "EU", "execution", 0, True, True),
        ("CFTC-37", "Swap Reporting", "CFTC", "US", "reporting", 0, True, True),
        ("FINRA-4210", "Margin Requirements", "FINRA", "US", "risk_control", 2_000_000, True, False),
        ("FCA-SUP16", "Transaction Reporting", "FCA", "GB", "reporting", 0, True, True),
        ("BCBS-LCR", "Liquidity Coverage Ratio", "Basel III", "Global", "risk_control", 100, True, False),
    ]

    rule_ids = []
    for code, name, reg, juris, cat, threshold, active, critical in rules_data:
        rid = gen_id()
        rule_ids.append(rid)
        rule = ComplianceRule(
            id=rid, org_id=org_id,
            rule_code=code, rule_name=name,
            regulation=reg, jurisdiction=juris,
            category=cat, description=f"{name} compliance requirement",
            threshold_value=float(threshold), threshold_unit="USD" if threshold > 0 else "percentage",
            comparison_operator="lte",
            is_active=active, is_critical=critical,
            effective_date=days_ago(365),
        )
        session.add(rule)
    session.flush()  # Ensure exchange connections and rules exist for FK references

    # Compliance events
    events_data = [
        ("pass", "SEC-15c3-5", "Order within daily limit", 8500000, 10000000, 0, "low", "resolved"),
        ("pass", "MiFID-II-BE", "Best execution verified", 0, 0, 0, "low", "resolved"),
        ("warning", "FINRA-4210", "Margin at 85% utilization", 85, 100, 15, "medium", "open"),
        ("pass", "CFTC-37", "Swap reported within T+1", 0, 0, 0, "low", "resolved"),
        ("fail", "FCA-SUP16", "Missing daily report", 0, 0, 100, "high", "open"),
        ("pass", "BCBS-LCR", "LCR at 115%", 115, 100, -15, "low", "resolved"),
    ]

    for etype, rule_code, desc, measured, threshold, dev, severity, status in events_data:
        event = ComplianceEvent(
            id=gen_id(), org_id=org_id,
            rule_id=rule_ids[0], exchange_connection_id=exchange_ids[0],
            event_type=etype, event_date=days_ago(1),
            description=desc, measured_value=float(measured),
            threshold_value=float(threshold), deviation_pct=float(dev),
            severity=severity, status=status,
        )
        session.add(event)

    # Counterparty risk scores
    counterparties = [
        ("Goldman Sachs", "bank", "A+", "US", 85, 82, 78, 80, 90, 83,
         5_000_000, 2_000_000, 10_000_000, 50, "approved", True),
        ("JPMorgan Chase", "bank", "AA-", "US", 88, 85, 80, 85, 92, 86,
         8_000_000, 3_000_000, 15_000_000, 53, "approved", True),
        ("HSBC", "bank", "A", "GB", 79, 75, 72, 78, 82, 77,
         4_000_000, 1_500_000, 8_000_000, 50, "approved", True),
        ("Standard Chartered", "bank", "A-", "GB", 72, 70, 68, 72, 75, 71,
         3_000_000, 1_000_000, 6_000_000, 50, "approved", True),
        ("Binance", "exchange", "NR", "Global", 65, 60, 55, 62, 58, 60,
         10_000_000, 5_000_000, 20_000_000, 50, "conditional", True),
        ("Kraken", "exchange", "NR", "US", 70, 65, 60, 68, 62, 65,
         5_000_000, 2_000_000, 10_000_000, 50, "approved", True),
    ]

    for name, ctype, rating, juris, credit, op, mkt, liq, reg, composite, exposure, pfe, limit, util, dd_status, docs in counterparties:
        cp = CounterpartyRiskScore(
            id=gen_id(), org_id=org_id,
            exchange_connection_id=exchange_ids[0],
            counterparty_name=name, counterparty_type=ctype,
            counterparty_rating=rating, jurisdiction=juris,
            credit_risk_score=credit, operational_risk_score=op,
            market_risk_score=mkt, liquidity_risk_score=liq,
            regulatory_risk_score=reg, composite_risk_score=composite,
            current_exposure=float(exposure), potential_future_exposure=float(pfe),
            exposure_limit=float(limit), utilization_pct=float(util),
            last_audit_date=days_ago(30), next_audit_date=days_ago(-90),
            due_diligence_status=dd_status, documents_verified=docs,
            recommendation="approved" if dd_status == "approved" else "conditional",
        )
        session.add(cp)

    # Trade orders
    orders_data = [
        ("buy", "treasury_bond", "US10Y-2034", 10_000_000, 100.25, "filled", "Goldman Sachs"),
        ("sell", "corporate_bond", "AA-CORP-2028", 5_000_000, 98.50, "filled", "JPMorgan Chase"),
        ("buy", "fx_swap", "EUR-USD-SPOT", 20_000_000, 1.0825, "pending_new", "HSBC"),
        ("buy", "treasury_bond", "UK15Y-2039", 8_000_000, 95.75, "filled", "Standard Chartered"),
        ("sell", "eurobond", "LATAM2030", 15_000_000, 92.00, "cancelled", "Goldman Sachs"),
    ]

    for side, itype, ident, qty, price, status, cp in orders_data:
        order = TradeOrder(
            id=gen_id(), org_id=org_id,
            exchange_connection_id=exchange_ids[0],
            order_reference=f"ORD-{gen_id()[:8]}",
            order_type="market", side=side,
            instrument_type=itype,
            instrument_identifier=ident,
            quantity=float(qty), price=float(price),
            total_value=float(qty * price),
            status=status,
            pre_trade_compliance_passed=True,
            post_trade_compliance_passed=(status == "filled"),
            created_by="Demo Admin",
        )
        session.add(order)

    # Risk allocations
    risk_allocs = [
        ("Market Risk Framework", "01.0", 60, 40, 70, 30, 80, 20, 90, 10, 50, 50,
         "Government bears 60% of market risk", "English Law", "ICC Arbitration"),
        ("Credit Risk Framework", "01.0", 40, 60, 30, 70, 50, 50, 80, 20, 40, 60,
         "Counterparty bears 60% of credit risk", "English Law", "LCIA Arbitration"),
        ("Operational Risk Framework", "01.0", 50, 50, 60, 40, 70, 30, 85, 15, 50, 50,
         "Shared operational risk", "New York Law", "AAA Arbitration"),
    ]

    for name, ver, mkt_g, mkt_c, cred_g, cred_c, op_g, op_c, liq_g, liq_c, sett_g, sett_c, desc, law, dispute in risk_allocs:
        alloc = RiskAllocation(
            id=gen_id(), org_id=org_id,
            exchange_connection_id=exchange_ids[0],
            framework_name=name, framework_version=ver,
            effective_date=days_ago(365),
            market_risk_allocation={"government": mkt_g, "counterparty": mkt_c},
            credit_risk_allocation={"government": cred_g, "counterparty": cred_c},
            operational_risk_allocation={"government": op_g, "counterparty": op_c},
            liquidity_risk_allocation={"government": liq_g, "counterparty": liq_c},
            settlement_risk_allocation={"government": sett_g, "counterparty": sett_c},
            max_government_loss=50_000_000,
            max_counterparty_loss=30_000_000,
            loss_sharing_trigger="Loss exceeds 20% of notional",
            dispute_resolution=dispute,
            governing_law=law,
            is_active=True,
            approved_by="Finance Minister",
            approval_date=days_ago(300),
        )
        session.add(alloc)

    # Ethical firewalls
    firewalls = [
        ("Minister of Finance", "Minister", "Ministry of Finance", "trading_blackout",
         "No trading during budget preparation", "Treasury", True),
        ("Deputy Secretary", "Deputy Secretary", "Ministry of Finance", "post_employment",
         "12-month cooling-off after leaving office", "Goldman Sachs", True),
        ("Budget Director", "Director", "Ministry of Budget", "conflict_of_interest",
         "No trading in entities under direct oversight", "Various", True),
    ]

    for name, role, dept, ctype, desc, entity, cooling in firewalls:
        fw = EthicalFirewall(
            id=gen_id(), org_id=org_id,
            person_name=name, person_role=role,
            person_department=dept, conflict_type=ctype,
            conflict_description=desc, related_entity=entity,
            detected_date=days_ago(90),
            cooling_off_start=days_ago(90),
            cooling_off_end=days_ago(-275) if cooling else days_ago(0),
            is_in_cooling_off=cooling,
            mitigation_action="Restricted trading access",
            is_resolved=not cooling,
            verified_by="Compliance Officer",
        )
        session.add(fw)

    # Regulatory reports
    reports = [
        ("form_pf", "xml", "SEC", "Form PF Quarterly Filing", "quarterly", "submitted", days_ago(5)),
        ("mifid_ii_transaction", "xml", "FCA", "MiFID II Transaction Report", "daily", "submitted", days_ago(1)),
        ("cftc_large_trader", "json", "CFTC", "Large Trader Report", "daily", "submitted", days_ago(1)),
        ("basel_iii_pillar3", "pdf", "PRA", "Basel III Pillar 3 Disclosure", "quarterly", "pending", None),
        ("dodd_frank_swap", "xml", "CFTC", "Dodd-Frank Swap Report", "real_time", "submitted", days_ago(1)),
    ]

    for rtype, fmt, authority, req, freq, status, filed in reports:
        report = RegulatoryReport(
            id=gen_id(), org_id=org_id,
            report_type=rtype, report_format=fmt,
            reporting_authority=authority,
            reporting_requirement=req,
            reporting_period_start=days_ago(90),
            reporting_period_end=days_ago(0),
            report_data={"status": status},
            report_hash=sha256_hash(f"{rtype}{filed}"),
            submission_status=status,
            submission_date=filed,
            is_valid=(status == "submitted"),
        )
        session.add(report)

    # Market data feeds
    feeds = [
        ("Treasury.gov Yield Curve", "official", "bond yields", 50000, 50, 99.5, True),
        ("ECB Exchange Rates", "official", "fx_rates", 60000, 45, 98.8, True),
        ("Bloomberg Terminal", "vendor", "market_data", 100, 10, 99.9, True),
        ("Yahoo Finance", "free", "equities", 1000, 100, 95.2, False),
        ("World Bank API", "official", "macro_indicators", 86400000, 200, 97.0, True),
    ]

    for name, ftype, instruments, freq, latency, quality, reliable in feeds:
        feed = MarketDataFeed(
            id=gen_id(), exchange_connection_id=exchange_ids[0],
            feed_name=name, feed_type=ftype,
            instruments=instruments,
            update_frequency_ms=freq, is_active=True,
            last_update=days_ago(0) if reliable else days_ago(3),
            latency_ms=latency, data_quality_score=quality,
            gap_count=0 if reliable else 5,
            error_count=0 if reliable else 2,
        )
        session.add(feed)

    # CCP clearing members
    ccp_data = [
        ("LCH.Clearnet", "GB", "active", 15_000_000, 50_000_000, 125.5, True, True, True, True),
        ("CME Clearing", "US", "active", 12_000_000, 40_000_000, 118.2, True, True, True, True),
        ("ICE Clear", "US", "active", 8_000_000, 25_000_000, 112.0, True, True, True, True),
        ("DTCC", "US", "pending", 10_000_000, 30_000_000, 0, True, False, False, False),
    ]

    for name, country, status, margin, df, stress, bonds, deriv, fx, port in ccp_data:
        ccp = CCPClearingMember(
            id=gen_id(), org_id=org_id,
            exchange_connection_id=exchange_ids[0],
            ccp_name=name, ccp_jurisdiction=country,
            membership_status=status,
            initial_margin_required=float(margin),
            default_fund_contribution=float(df),
            stress_test_coverage=float(stress) if stress > 0 else None,
            supports_bonds=bonds, supports_derivatives=deriv,
            supports_fx=fx,
            is_compliant=(status == "active"),
            last_audit_date=days_ago(30) if status == "active" else None,
        )
        session.add(ccp)

    # Smart contract templates
    contracts = [
        ("Bond Purchase Agreement", "purchase", "solidity",
         "pragma solidity ^0.8.0; contract BondPurchase { ... }",
         ["KYC_verified", "compliance_approved"],
         ["settlement_date_reached", "all_conditions_met"],
         ["transfer_bonds", "transfer_funds"],
         50_000_000, True, 10_000_000, True, "passed"),
        ("FX Hedging Contract", "hedge", "solidity",
         "pragma solidity ^0.8.0; contract FXHedge { ... }",
         ["hedging_authorization", "counterparty_approved"],
         ["fx_rate_threshold", "date_trigger"],
         ["execute_fx_swap", "settle_difference"],
         20_000_000, True, 5_000_000, True, "passed"),
        ("Repo Agreement", "repo", "solidity",
         "pragma solidity ^0.8.0; contract Repo { ... }",
         ["collateral_verified", "haircut_applied"],
         ["maturity_date", "margin_call_triggered"],
         ["return_collateral", "pay_repo_rate"],
         30_000_000, True, 8_000_000, True, "passed"),
    ]

    for name, ctype, chain, code, pre, triggers, actions, max_val, human, threshold, halt, audit in contracts:
        template = SmartContractTemplate(
            id=gen_id(), org_id=org_id,
            template_name=name, template_type=ctype,
            version="1.0.0", blockchain=chain,
            contract_code=code,
            pre_conditions=pre,
            execution_triggers=triggers,
            settlement_logic=actions,
            max_value_per_execution=float(max_val),
            requires_human_approval=human,
            approval_threshold=float(threshold),
            emergency_halt_enabled=halt,
            code_hash=sha256_hash(code),
            last_audit_date=days_ago(60),
            audit_result=audit,
            is_active=True,
        )
        session.add(template)

    # Institutional capacity assessment
    assessment = InstitutionalCapacityAssessment(
        id=gen_id(), org_id=org_id,
        assessment_date=days_ago(30),
        assessor="Deloitte Advisory",
        assessment_period="Q3 2024",
        hr_score=75, hr_details="Experienced legal team, limited data analytics talent",
        tech_score=68, tech_details="Legacy IT systems, manual reporting processes",
        process_score=80, process_details="Strong regulatory framework, existing audit infrastructure",
        governance_score=82, governance_details="Clear governance structure, board oversight",
        data_quality_score=72, data_quality_details="Manual data collection, some inconsistencies",
        composite_score=75.4,
        rating="ready_with_conditions",
        exchange_readiness="Partially ready — requires technology upgrades",
        gaps=["Automated reporting", "Real-time monitoring", "API integrations"],
        recommendations=["Hire 3 data analysts", "Upgrade reporting systems", "Quarterly training"],
    )
    session.add(assessment)

    # Algorithm audit trail
    audit_entries = [
        ("debt_optimizer", "model_execution", "Sovereign Debt Optimizer executed optimization",
         {"portfolio_id": "demo", "objective": "minimize_cost"}, 0.89, 1250,
         "approved", "Dr. Sarah Chen"),
        ("risk_engine", "alert_generated", "Early Warning System flagged Argentina as high-risk",
         {"risk_score": 85, "confidence": 0.94}, 0.94, 850,
         "acknowledged", "Risk Committee"),
        ("compliance_check", "rule_evaluation", "SEC Rule 15c3-5 compliance check passed",
         {"daily_exposure": 8500000, "limit": 10000000}, 1.0, 150,
         "auto_approved", "System"),
    ]

    for module, etype, desc, summary, conf, exec_ms, review, reviewer in audit_entries:
        entry_hash = sha256_hash(f"{module}{etype}{desc}{now().isoformat()}")
        input_hash = sha256_hash(str(summary))
        audit = AlgorithmAuditTrail(
            id=gen_id(), org_id=org_id,
            event_type=etype, event_timestamp=days_ago(1),
            event_description=desc,
            input_data_hash=input_hash,
            input_data_summary=summary,
            confidence_score=conf,
            execution_time_ms=exec_ms,
            output_value={"result": review, "confidence": conf},
            human_review_required=(review != "auto_approved"),
            human_reviewed=True,
            reviewed_by=reviewer,
            review_outcome=review,
            event_hash=entry_hash,
            previous_event_hash=sha256_hash("previous"),
        )
        session.add(audit)

    session.commit()
    print(f"  Created {len(exchanges)} exchanges, {len(rules_data)} compliance rules, {len(counterparties)} counterparties")


def seed_broker_integration(session, org_id):
    print("[5/8] Seeding Broker Integration data...")

    # KYC records
    kyc_data = [
        ("Ministry of Finance - Demo Republic", "treasury", "US", "low", 15, True, True, False),
        ("Gulf Sovereign Wealth Fund", "sovereign_wealth", "AE", "medium", 35, True, True, False),
        ("National Pension Fund - Demo", "pension_fund", "GB", "low", 20, True, True, False),
        ("Central Bank of Demo", "central_bank", "SG", "low", 10, True, True, False),
        ("Emerging Markets Dev Fund", "sovereign_wealth", "NG", "high", 65, True, True, True),
        ("Nordic Investment Authority", "sovereign_wealth", "NO", "low", 12, True, True, False),
    ]

    kyc_ids = []
    for name, ctype, jurisdiction, risk, score, cip, cdd, edd in kyc_data:
        kid = gen_id()
        kyc_ids.append(kid)
        kyc = ClientKYC(
            id=kid, org_id=org_id,
            client_name=name, client_type=ctype,
            jurisdiction=jurisdiction,
            risk_level=risk, risk_score=score,
            cip_verified=cip, cip_date=days_ago(60),
            cip_documents=["government_decree", "board_resolution", "authorized_signatories"],
            cip_verification_method="documentary",
            cdd_status="approved", cdd_date=days_ago(45),
            beneficial_ownership=[{"name": name, "ownership_pct": 100, "role": "sole_owner"}],
            source_of_funds="Government budget appropriation",
            source_of_wealth="Sovereign wealth",
            expected_activity={"monthly_volume": 100_000_000},
            edd_required=edd,
            sanctions_screening={"screened": True, "matches": [], "status": "clear"},
            kyc_status="approved",
            approved_by="Compliance Officer",
            approval_date=days_ago(30),
            next_review_date=days_ago(-365),
            ongoing_monitoring_frequency="annual" if risk == "low" else "quarterly",
        )
        session.add(kyc)

    # Client onboarding
    onboarding_data = [
        (kyc_ids[0], "Ministry of Finance - Demo Republic", "treasury", "US",
         "active", "cash",
         ["government_decree", "board_resolution", "authorized_signatories"],
         {"bank_name": "JPMorgan Chase", "swift": "CHASUS33", "currency": "USD"}),
        (kyc_ids[1], "Gulf Sovereign Wealth Fund", "sovereign_wealth", "AE",
         "kyc_review", "custody",
         ["government_decree", "board_resolution"],
         {"bank_name": "HSBC", "swift": "HSBCGB2L", "currency": "USD"}),
        (kyc_ids[2], "National Pension Fund - Demo", "pension_fund", "GB",
         "account_setup", "cash",
         ["trust_deed", "investment_policy", "actuarial_report"],
         {"bank_name": "Barclays", "swift": "BARCGB22", "currency": "GBP"}),
    ]

    for kyc_id, name, ctype, jurisdiction, stage, atype, required, settlement in onboarding_data:
        onb = ClientOnboarding(
            id=gen_id(), org_id=org_id, kyc_id=kyc_id,
            client_name=name, client_type=ctype,
            jurisdiction=jurisdiction,
            stage=stage, account_type=atype,
            documents_required=required,
            documents_submitted=required[:2],
            settlement_instructions=settlement,
            target_completion_date=days_ago(-30),
            stage_history=[
                {"stage": "initiated", "date": days_ago(60).isoformat()},
                {"stage": stage, "date": days_ago(15).isoformat()},
            ],
        )
        session.add(onb)

    # Transaction records
    transactions = [
        ("buy", "treasury_bond", "US10Y-2034", 5_000_000, 100.25, False, None, "reviewed"),
        ("sell", "corporate_bond", "AA-CORP-2028", 2_000_000, 98.50, False, None, "reviewed"),
        ("buy", "fx_swap", "EUR-USD-SPOT", 10_000_000, 1.0825, True, "medium", "pending"),
        ("buy", "treasury_bond", "UK15Y-2039", 3_000_000, 95.75, False, None, "reviewed"),
        ("sell", "eurobond", "LATAM2030", 8_000_000, 92.00, True, "high", "escalated"),
        ("buy", "t_bill", "US3M-2024", 15_000_000, 99.50, False, None, "reviewed"),
        ("sell", "domestic_bond", "LOCAL7Y-2031", 4_000_000, 97.25, False, None, "reviewed"),
        ("buy", "sovereign_bond", "DEMO20Y-2044", 7_000_000, 88.00, True, "high", "escalated"),
    ]

    for ttype, itype, ident, qty, price, suspicious, severity, review in transactions:
        txn = TransactionRecord(
            id=gen_id(), org_id=org_id,
            kyc_id=kyc_ids[0],
            transaction_type=ttype, instrument_type=itype,
            instrument_identifier=ident,
            quantity=float(qty), price=float(price),
            total_value=float(qty * price), currency="USD",
            is_suspicious=suspicious,
            alert_severity=severity,
            alert_reasons=["large_transaction"] if suspicious else [],
            review_status=review,
            reviewed_by="Compliance Officer" if review == "reviewed" else None,
        )
        session.add(txn)

    # Transaction monitoring rules
    rules = [
        ("Large Transaction Alert", "threshold", 10_000_000, "medium", "Alerts on transactions > $10M"),
        ("Very Large Transaction Alert", "threshold", 50_000_000, "high", "Alerts on transactions > $50M"),
        ("Daily Volume Limit", "velocity", 100_000_000, "high", "Alerts when daily volume > $100M"),
        ("Structuring Detection", "pattern", 9_500_000, "high", "Multiple transactions below threshold"),
        ("Sanctions Screening", "sanctions", 0, "critical", "OFAC/EU/UN sanctions lists"),
        ("Unusual Pattern", "pattern", 5_000_000, "medium", "Unusual trading patterns"),
    ]

    for name, rtype, threshold, severity, desc in rules:
        rule = TransactionMonitoringRule(
            id=gen_id(), org_id=org_id,
            rule_name=name, rule_type=rtype,
            description=desc, is_active=True,
            threshold_value=float(threshold),
            threshold_currency="USD",
            alert_severity=severity,
            auto_escalate=severity in ("high", "critical"),
            require_sar=severity == "critical",
        )
        session.add(rule)

    # Broker registrations
    registrations = [
        ("form_bd", "SEC", "CRD-888888", "approved", days_ago(365), days_ago(300)),
        ("finra_membership", "FINRA", "CRD-888888", "approved", days_ago(365), days_ago(280)),
        ("state_registration", "State of New York", None, "approved", days_ago(300), days_ago(250)),
        ("government_securities", "SEC (Section 15C)", "CRD-888888", "approved", days_ago(365), days_ago(300)),
    ]

    for rtype, regulator, crd, status, filed, approved in registrations:
        reg = BrokerRegistration(
            id=gen_id(), org_id=org_id,
            registration_type=rtype, regulator=regulator,
            crd_number=crd, status=status,
            filing_date=filed, approval_date=approved,
            requirements=[{"requirement": "net_capital", "status": "met"}],
            expiration_date=days_ago(-365),
            renewal_required=True,
        )
        session.add(reg)

    # Fee schedules
    fee_schedules = [
        ("Sovereign Wealth Standard", "sovereign_wealth", "bps_of_volume", 3.0, 500,
         0.05, 0.02,
         [{"min_volume": 0, "commission_bps": 5}, {"min_volume": 50_000_000, "commission_bps": 3}]),
        ("Central Bank Preferred", "central_bank", "bps_of_volume", 2.0, 250,
         0.02, 0.01,
         [{"min_volume": 0, "commission_bps": 3}, {"min_volume": 100_000_000, "commission_bps": 2}]),
        ("Pension Fund Standard", "pension_fund", "bps_of_volume", 4.0, 750,
         0.04, 0.015,
         [{"min_volume": 0, "commission_bps": 6}, {"min_volume": 30_000_000, "commission_bps": 4}]),
    ]

    for name, ctype, comm_type, comm_val, min_comm, custody_pct, mgmt_pct, tiers in fee_schedules:
        schedule = FeeSchedule(
            id=gen_id(), org_id=org_id,
            schedule_name=name, client_type=ctype,
            effective_date=days_ago(180),
            commission_type=comm_type,
            commission_value=comm_val,
            minimum_commission=float(min_comm),
            custody_fee_annual_pct=custody_pct,
            management_fee_annual_pct=mgmt_pct,
            volume_tiers=tiers,
            settlement_fee=25.0, wire_fee=35.0,
            account_maintenance_fee=0,
        )
        session.add(schedule)

    # Best execution records
    best_exec = [
        ("treasury_bond", "market", "buy", 5_000_000, 100.25,
         [{"venue": "NYSE", "estimated_price": 100.25, "estimated_spread_bps": 2},
          {"venue": "LSE", "estimated_price": 100.28, "estimated_spread_bps": 3}],
         "NYSE", "Best price and fastest execution", 100.24, 100.25),
        ("corporate_bond", "limit", "sell", 2_000_000, 98.50,
         [{"venue": "LSE", "estimated_price": 98.48, "estimated_spread_bps": 4},
          {"venue": "NYSE", "estimated_price": 98.50, "estimated_spread_bps": 3}],
         "NYSE", "Higher price achieved", 98.52, 98.50),
    ]

    for itype, otype, side, qty, price, venues, selected, reason, actual, bench in best_exec:
        record = BestExecutionRecord(
            id=gen_id(), org_id=org_id,
            instrument_type=itype, order_type=otype,
            side=side, quantity=float(qty),
            venues_analyzed=venues,
            selected_venue=selected, selection_reason=reason,
            actual_price=actual, benchmark_price=bench,
            price_improvement_bps=(actual - bench) / bench * 10000,
            best_execution_confirmed=True,
        )
        session.add(record)

    session.commit()
    print(f"  Created {len(kyc_data)} KYC records, {len(onboarding_data)} onboarding, {len(transactions)} transactions")


# ── 9. Regulatory Compliance ─────────────────────────────────────────

def seed_regulatory_compliance(session, org_id):
    print("[9/9] Seeding regulatory compliance data...")

    # Certifications
    certs_data = [
        ("EU AI Act High-Risk Compliance", "eu_ai_act", "European Commission", "EU", "certified",
         92.5, 95.0, True, True, True, 88.0),
        ("SEC Algorithmic Trading Rule 15c3-5", "sec_algo", "Securities and Exchange Commission", "US", "certified",
         87.3, 91.0, True, True, True, 85.0),
        ("ESMA AI Transparency Framework", "esma_ai", "European Securities and Markets Authority", "EU", "in_progress",
         74.2, 82.0, True, True, False, 72.0),
        ("ISO 27001 Information Security", "iso_27001", "International Organization for Standardization", "Global", "certified",
         96.8, 98.0, True, True, True, 95.0),
    ]
    cert_count = 0
    for name, ctype, authority, juris, status, score, dq, dl, tr, dl_log, audit in certs_data:
        cert = RegulatoryCertification(
            id=gen_id(), org_id=org_id,
            certification_name=name, certification_type=CertificationType(ctype),
            issuing_authority=authority, jurisdiction=juris,
            status=CertificationStatus(status), compliance_score=score,
            conformity_assessment_date=days_ago(30),
            conformity_assessment_result="pass" if status == "certified" else "conditional_pass",
            conformity_findings=[{"finding": "Minor documentation gap", "severity": "low", "remediation": "Updated SOP v2.3"}],
            data_quality_score=dq, data_lineage_verified=dl,
            traceability_enabled=tr, decision_logging_enabled=dl_log,
            audit_trail_completeness=audit,
            issued_date=days_ago(365) if status == "certified" else None,
            expiry_date=future_days(365) if status == "certified" else None,
            last_audit_date=days_ago(30),
            next_audit_date=future_days(90),
        )
        session.add(cert)
        cert_count += 1

    # Impact assessments
    aia_data = [
        ("Sovereign Debt Optimizer v2.1 Impact", "DebtOptimizer", "2.1", "Dr. Elena Vasquez", "Independent AI Ethics Board",
         "high", 72.5, 65.0, 58.0, "passed", 0.94, 0.03),
        ("Early Warning System Validation", "EarlyWarningEngine", "3.0", "Prof. James Chen", "MIT Computer Science Lab",
         "critical", 85.2, 78.0, 71.0, "passed", 0.91, 0.05),
        ("Market Intelligence NLP Assessment", "MarketNLP", "1.8", "Dr. Aisha Patel", "Stanford AI Governance",
         "medium", 45.8, 42.0, 35.0, "conditional", 0.87, 0.08),
    ]
    aia_count = 0
    for name, model, ver, assessor, org, severity, risk, systemic, mkt, val, acc, bias in aia_data:
        aia = AlgorithmicImpactAssessment(
            id=gen_id(), org_id=org_id,
            assessment_name=name, model_name=model, model_version=ver,
            assessor_name=assessor, assessor_organization=org,
            impact_severity=ImpactSeverity(severity),
            risk_score=risk, systemic_risk_score=systemic, market_impact_score=mkt,
            validation_status=ValidationStatus(val),
            independent_validator=assessor,
            validation_date=days_ago(15),
            validation_findings=[{"finding": "Model performs within acceptable parameters", "recommendation": "Continue monitoring"}],
            training_data_period="2020-2026", training_data_size=50000,
            model_accuracy=acc, model_bias_score=bias,
            fairness_metrics={"demographic_parity": 0.92, "equalized_odds": 0.89},
            kill_switch_enabled=True,
            position_limits={"max_single_position_pct": 5.0, "max_sector_pct": 25.0},
            circuit_breakers={"drawdown_limit_pct": 10.0, "daily_loss_limit_pct": 3.0},
            human_oversight_required=True,
            findings_summary=f"Comprehensive assessment of {model} completed. All critical controls verified.",
            recommendations=["Maintain current monitoring frequency", "Update training data quarterly"],
            assessment_date=days_ago(30),
            review_date=days_ago(15),
            next_assessment_date=future_days(90),
        )
        session.add(aia)
        aia_count += 1

    # Stress tests
    st_data = [
        ("2008 GFC Replay", "historical", "Global Financial Crisis Replay", "Replay of 2008 crisis conditions with modern portfolio",
         -35.0, 180, "interest_rate", 200.0, -25.0, -45.0, 350.0, "passed", -18.5, -22.3, 120, "high", False, False),
        ("Flash Crash Scenario", "hypothetical", "May 2010 Flash Crash", "Simulated 1000-point Dow drop in 5 minutes",
         -15.0, 1, "equity", 0.0, -5.0, -30.0, 0.0, "passed", -8.2, -12.1, 5, "critical", True, True),
        ("Sovereign Default Cascade", "scenario", "Multi-Country Default", "Simultaneous default by 3 emerging market sovereigns",
         -45.0, 365, "credit", 500.0, -10.0, -20.0, 800.0, "marginal", -32.1, -38.7, 240, "high", False, False),
        ("Rate Shock +1000bps", "sensitivity", "Parallel Rate Shock", "Immediate 1000bps parallel shift upward",
         -28.0, 30, "interest_rate", 1000.0, 0.0, -15.0, 0.0, "passed", -21.4, -25.8, 90, "medium", False, False),
        ("Monte Carlo VaR 99%", "monte_carlo", "99% VaR Stress", "10,000 path Monte Carlo simulation at 99% confidence",
         -22.0, 90, "all", 0.0, -8.0, -18.0, 200.0, "passed", -15.7, -19.2, 60, "medium", False, False),
    ]
    st_count = 0
    for name, ttype, scenario, desc, shock, dur, mkt, ir, fx, eq, credit, result, impact, dd, recov, liq, cb, halt in st_data:
        st = StressTest(
            id=gen_id(), org_id=org_id,
            test_name=name, test_type=StressTestType(ttype),
            scenario_name=scenario, scenario_description=desc,
            shock_magnitude_pct=abs(shock), duration_days=dur,
            affected_markets=[mkt],
            interest_rate_shock_bps=ir, fx_shock_pct=fx,
            equity_shock_pct=eq, credit_spread_shock_bps=credit,
            result=StressTestResultStatus(result),
            portfolio_impact_pct=impact, max_drawdown_pct=dd,
            recovery_time_days=recov, liquidity_impact=liq,
            flash_crash_threshold_bps=500.0,
            circuit_breaker_triggered=cb, auto_halt_triggered=halt,
            risk_metrics={"var_99": abs(impact) * 0.8, "cvar_99": abs(impact) * 1.2},
            recommendations=["Review position limits", "Update hedging strategy"],
            executed_by="Risk Committee",
            execution_date=days_ago(7),
        )
        session.add(st)
        st_count += 1

    # Cross-border settlements
    settlement_data = [
        ("SET-2026-001", "swift", "US", "GB", "USD", "GBP", 50000000, 0.79, "Barclays Bank", "settled", True, True, True, None),
        ("SET-2026-002", "target2", "DE", "FR", "EUR", "EUR", 75000000, 1.0, "Deutsche Bundesbank", "settled", True, True, True, None),
        ("SET-2026-003", "blockchain_public", "US", "SG", "USD", "SGD", 30000000, 1.35, "DBS Bank", "in_progress", True, True, True, "0x7f9e8c...abc123"),
        ("SET-2026-004", "fedwire", "US", "JP", "USD", "JPY", 100000000, 149.5, "Mizuho Bank", "pending", False, False, False, None),
        ("SET-2026-005", "cips", "CN", "US", "CNY", "USD", 200000000, 0.138, "ICBC", "settled", True, True, True, None),
    ]
    set_count = 0
    for ref, net, orig_j, dest_j, orig_c, dest_c, amt, rate, cp, status, comp, aml, sanction, tx_hash in settlement_data:
        s = CrossBorderSettlement(
            id=gen_id(), org_id=org_id,
            settlement_reference=ref,
            settlement_network=SettlementNetwork(net),
            origin_jurisdiction=orig_j, destination_jurisdiction=dest_j,
            origin_currency=orig_c, destination_currency=dest_c,
            amount_origin=amt, amount_destination=amt * rate,
            exchange_rate=rate, fx_spread_bps=2.5,
            counterparty_name=cp,
            status=SettlementStatus(status),
            settlement_date=days_ago(3) if status == "settled" else None,
            compliance_checks_passed=comp,
            aml_screening_passed=aml,
            sanctions_screening_passed=sanction,
            blockchain_tx_hash=tx_hash,
            blockchain_network="Ethereum" if tx_hash else None,
            settlement_fees=amt * 0.0001,
        )
        session.add(s)
        set_count += 1

    # Explainability disclosures
    disc_data = [
        ("model_card", "Sovereign Debt Optimizer - Model Card", "Regulators", "published", "1.0",
         "This model optimizes sovereign debt portfolios using quantum-inspired algorithms.",
         "Weighted KNN classification with real-time market data feeds."),
        ("technical_report", "Early Warning System - Technical Report", "Technical Auditors", "published", "2.1",
         "Technical deep-dive into the early warning system architecture and performance.",
         "Ensemble methods combining rule-based triggers with ML-based anomaly detection."),
        ("consumer_summary", "AI Governance Summary for Public Disclosure", "General Public", "published", "1.0",
         "Plain-language summary of how AI is used in sovereign debt management.",
         "Simple averaging and threshold-based decision rules with human oversight."),
        ("regulatory_filing", "SEC Algorithmic Trading Disclosure", "SEC", "under_review", "1.2",
         "Formal regulatory filing for algorithmic trading compliance.",
         "Multi-factor risk model with circuit breakers and kill switches."),
        ("transparency_report", "Annual AI Transparency Report", "Board of Directors", "draft", "1.0",
         "Annual report on AI system performance, incidents, and governance.",
         "Comprehensive review of all AI systems including bias testing and accuracy metrics."),
    ]
    disc_count = 0
    for dtype, title, audience, status, ver, summary, method in disc_data:
        d = ExplainabilityDisclosure(
            id=gen_id(), org_id=org_id,
            disclosure_type=DisclosureType(dtype),
            title=title, target_audience=audience,
            status=DisclosureStatus(status), version=ver,
            executive_summary=summary,
            methodology_description=method,
            feature_contributions=[{"feature": "debt_to_gdp", "importance": 0.35}, {"feature": "reserve_coverage", "importance": 0.28}],
            limitations_and_biases=["Model trained on historical data may not predict unprecedented events", "Exchange rate assumptions use forward curves"],
            data_sources_used=["Treasury.gov", "World Bank", "ECB", "Yahoo Finance"],
            regulatory_references=["EU AI Act Article 6", "SEC Rule 15c3-5", "MiFID II Article 17"],
            publication_date=days_ago(30) if status == "published" else None,
            review_date=days_ago(15),
            next_review_date=future_days(90),
        )
        session.add(d)
        disc_count += 1

    session.commit()
    print(f"  Created {cert_count} certifications, {aia_count} impact assessments, {st_count} stress tests, {set_count} settlements, {disc_count} disclosures")



# --- 10. Exchange Due Diligence ---

def seed_exchange_due_diligence(session, org_id):
    print("[10/10] Seeding exchange due diligence data...")

    # Pre-trade controls
    controls_data = [
        ("Daily Volume Limit", "volume_limit", "Maximum daily trading volume", 100000000, 80, "USD", True),
        ("Price Collar - Treasury Bonds", "price_collar", "Price must stay within 5% of VWAP", 5.0, 90, "percentage", True),
        ("Self-Trade Avoidance", "self_trade_avoidance", "Prevent self-trading across all accounts", 0, 100, "USD", True),
        ("Position Limit - Single Issuer", "position_limit", "Max position in single sovereign bond", 25000000, 85, "USD", True),
        ("Order Size Limit", "order_size_limit", "Max single order size", 5000000, 80, "USD", True),
        ("Flash Crash Circuit Breaker", "circuit_breaker", "Halt trading if index drops >3% in 5 min", 3.0, 100, "percentage", True),
        ("Kill Switch", "kill_switch", "Emergency stop for all trading activity", 1, 100, "activation", True),
    ]
    ctrl_count = 0
    for name, ctype, desc, max_val, warn, curr, reject in controls_data:
        ctrl = PreTradeControl(
            id=gen_id(), org_id=org_id,
            control_name=name, control_type=ControlType(ctype),
            description=desc, status=ControlStatus.ACTIVE,
            max_value=max_val, warning_threshold_pct=warn, currency=curr,
            time_window_minutes=60 if ctype != "circuit_breaker" else 5,
            reject_on_breach=reject, alert_on_breach=True,
            self_trade_enabled=(ctype == "self_trade_avoidance"),
            price_collar_upper_pct=max_val if ctype == "price_collar" else None,
            price_collar_lower_pct=-max_val if ctype == "price_collar" else None,
            reference_price_source="VWAP" if ctype == "price_collar" else None,
            escalation_contacts=["risk@quantive.com", "compliance@quantive.com"],
            total_checks=1250 + ctrl_count * 200,
            total_breaches=ctrl_count,
            last_breach_date=days_ago(30 + ctrl_count * 5) if ctrl_count < 3 else None,
            last_check_date=days_ago(1),
        )
        session.add(ctrl)
        ctrl_count += 1

    # Simulation environments
    sims_data = [
        ("NYSE Treasury Bond Simulation", "NYSE", ["treasury_bond"], "2023-01 to 2026-08", 50000000, 5.0, 1.5,
         "completed", 1250, 2850000, 1.85, -8.2, 62.4, 4.8, 3.2, False, False),
        ("LSE Gilt Trading Simulation", "LSE", ["government_bond"], "2022-06 to 2026-08", 30000000, 8.0, 2.0,
         "completed", 890, 1420000, 1.42, -12.5, 58.1, 7.2, 4.8, False, True),
        ("Crypto Exchange - BTC/ETH", "Binance", ["crypto"], "2024-01 to 2026-08", 20000000, 2.0, 3.0,
         "completed", 2100, 4200000, 2.15, -15.3, 55.8, 1.8, 5.2, True, False),
        ("Flash Crash Resilience Test", "NYSE", ["equity", "bond"], "2010-05 to 2010-06", 100000000, 0.5, 0.5,
         "running", 0, 0, None, None, None, 0.3, 0, False, False),
    ]
    sim_count = 0
    for name, venue, instruments, period, capital, lat, slip, status, trades, pnl, sharpe, dd, win, avg_lat, rej, ks, cb in sims_data:
        sim = SimulationEnvironment(
            id=gen_id(), org_id=org_id,
            environment_name=name, exchange_venue=venue,
            instrument_types=instruments, historical_period=period,
            starting_capital=capital, simulated_latency_ms=lat,
            slippage_bps=slip, fill_rate_pct=95.0 - rej,
            status=SimulationStatus(status),
            total_trades=trades, total_pnl=pnl,
            sharpe_ratio=sharpe, max_drawdown_pct=dd,
            win_rate_pct=win, avg_latency_ms=avg_lat,
            fill_rejection_rate_pct=rej,
            pre_trade_controls_tested=["volume_limit", "price_collar", "circuit_breaker"],
            kill_switch_triggered=ks, circuit_breaker_triggered=cb,
            start_date=days_ago(90) if status == "completed" else days_ago(7),
            end_date=days_ago(30) if status == "completed" else None,
        )
        session.add(sim)
        sim_count += 1

    # Market surveillance alerts
    alerts_data = [
        ("unusual_volume", "medium", "open", "Unusual Volume Spike in 10Y Treasury", "Volume 3x average detected in US10Y-2034", "US10Y-2034", 0.78, 100.25, 5000000, None),
        ("spoofing", "high", "investigating", "Potential Spoofing Detected", "Large order placed and cancelled within 50ms", "UK15Y-2039", 0.85, 95.75, 2000000, "Risk Committee"),
        ("wash_trading", "critical", "escalated", "Wash Trading Pattern Identified", "Circular trading between 3 related accounts", "LATAM2030", 0.92, 92.00, 8000000, "Compliance Officer"),
        ("front_running", "high", "open", "Suspicious Pre-Announcement Activity", "Large buy order 2 min before rate decision", "DEMO20Y-2044", 0.88, 88.00, 7000000, None),
        ("flash_crash_risk", "medium", "resolved", "Elevated Volatility Alert", "VIX spike to 28, monitoring for cascade", None, 0.65, None, None, "Automated System"),
        ("manipulation", "low", "false_positive", "Pattern Analysis - Normal Flow", "Initial flag resolved as institutional rebalancing", "US3M-2024", 0.45, 99.50, 15000000, "Risk Committee"),
    ]
    alert_count = 0
    for atype, sev, status, title, desc, ident, conf, price, vol, assigned in alerts_data:
        alert = MarketSurveillance(
            id=gen_id(), org_id=org_id,
            alert_type=SurveillanceAlertType(atype),
            severity=SurveillanceSeverity(sev),
            status=SurveillanceStatus(status),
            title=title, description=desc,
            instrument_identifier=ident,
            affected_accounts=["account_001", "account_002"],
            detection_rule=f"rule_{atype}_v2",
            confidence_score=conf,
            evidence=[{"type": "order_book_snapshot", "timestamp": days_ago(1).isoformat()}],
            price_at_detection=price, volume_at_detection=vol,
            assigned_to=assigned,
            detected_at=days_ago(7 + alert_count),
        )
        session.add(alert)
        alert_count += 1

    # Proof of reserves
    reserves_data = [
        ("Sovereign Bond Reserve - Custodian A", "State Street", "US", 500000000, 485000000, "USD", "ethereum", "verified", True),
        ("Gold Reserve - allocated", "HSBC Vault", "GB", 250000000, 248000000, "USD", None, "verified", False),
        ("Stablecoin Reserve - USDC", "Coinbase", "US", 100000000, 99500000, "USD", "ethereum", "verified", True),
        ("Multi-Chain Treasury Reserve", "BitGo", "US", 75000000, 74200000, "USD", "multi_chain", "pending", True),
    ]
    por_count = 0
    for name, custodian, juris, reserves, liabilities, curr, chain, status, zkp in reserves_data:
        ratio = reserves / liabilities * 100 if liabilities > 0 else 100
        por = ProofOfReserve(
            id=gen_id(), org_id=org_id,
            reserve_name=name, custodian_name=custodian, jurisdiction=juris,
            total_reserves=reserves, total_liabilities=liabilities,
            reserve_ratio_pct=ratio, excess_reserves=reserves - liabilities,
            currency=curr,
            chain=ReserveChain(chain) if chain else None,
            tx_hash=f"0x{gen_id()[:16]}..." if chain else None,
            block_number=19000000 + por_count * 1000 if chain else None,
            attestation_service="Chainlink" if chain else None,
            status=ReserveStatus(status),
            verification_date=days_ago(1) if status == "verified" else None,
            next_verification_date=future_days(30),
            auditor_name="Deloitte" if not zkp else "Custom ZKP Circuit",
            zero_knowledge_proof=zkp,
            zkp_circuit_id=f"zkp_circuit_{por_count}" if zkp else None,
        )
        session.add(por)
        por_count += 1

    # Decision logs
    decisions_data = [
        ("trade_execution", "EXEC-001", "treasury_bond", "US10Y-2034", "buy", 5000000, 100.25,
         "DebtOptimizer", "2.1", 0.89, {"debt_to_gdp": 0.35, "reserve_coverage": 0.28, "yield_curve": 0.22},
         "Buy recommendation based on favorable yield spread and low default risk", True, False),
        ("risk_alert", "RISK-001", "corporate_bond", "AA-CORP-2028", "hold", 2000000, 98.50,
         "EarlyWarningEngine", "3.0", 0.72, {"credit_spread": 0.42, "issuer_health": 0.31},
         "Credit spread widening - recommend reducing exposure", True, True),
        ("rebalance", "REB-001", "sovereign_bond", "DEMO20Y-2044", "sell", 7000000, 88.00,
         "DebtOptimizer", "2.1", 0.91, {"maturity_mismatch": 0.38, "duration_target": 0.29},
         "Rebalance to reduce duration exposure ahead of rate decision", True, False),
        ("compliance_check", "COMP-001", "fx_swap", "EUR-USD-SPOT", "execute", 10000000, 1.0825,
         None, None, 1.0, {"aml_check": 1.0, "sanctions_check": 1.0},
         "All compliance checks passed - AML, sanctions, and counterparty verified", False, False),
        ("kill_switch", "KS-001", None, None, "halt_all", None, None,
         None, None, 1.0, {"vix_level": 0.65, "circuit_breaker": 0.35},
         "Kill switch activated due to VIX > 25 and rapid volume spike", False, False),
    ]
    dl_count = 0
    for dtype, did, itype, ident, action, qty, price, model, ver, conf, shap, explanation, human_req, human_rev in decisions_data:
        event_hash = sha256_hash(f"{did}{dtype}{action}{now().isoformat()}")
        dl = DecisionLog(
            id=gen_id(), org_id=org_id,
            decision_type=DecisionType(dtype), decision_id=did,
            instrument_type=itype, instrument_identifier=ident,
            action=action, side="buy" if action == "buy" else "sell" if action == "sell" else None,
            quantity=float(qty) if qty else None, price=float(price) if price else None,
            total_value=float(qty * price) if qty and price else None,
            model_name=model, model_version=ver,
            confidence_score=conf,
            feature_contributions=[{"feature": k, "importance": v} for k, v in shap.items()],
            shap_values=shap,
            explanation_text=explanation,
            pre_trade_checks_passed=True,
            human_review_required=human_req,
            human_reviewed=human_rev,
            reviewed_by="Risk Committee" if human_rev else None,
            review_outcome="approved" if human_rev else None,
            event_hash=event_hash,
            previous_event_hash=sha256_hash("previous"),
        )
        session.add(dl)
        dl_count += 1

    session.commit()
    print(f"  Created {ctrl_count} pre-trade controls, {sim_count} simulations, {alert_count} surveillance alerts, {por_count} proof of reserves, {dl_count} decision logs")


# ── Section 11: Cybersecurity, Privacy & Interoperability ──────────────

def seed_cybersecurity_privacy(session, org_id):
    print()
    print("[11/11] Seeding cybersecurity, privacy & interoperability data...")

    mon_count = sec_count = pri_count = int_count = 0

    # ── Regulatory Monitoring ──
    monitors = [
        {"name": "Treasury Trading Model Monitor", "desc": "Real-time monitoring of the sovereign debt trading ML model", "model": "DebtOptimizer_v2", "version": "2.1.0", "interval": 30, "accuracy_thresh": 0.92, "latency_thresh": 50.0, "drift_thresh": 3.0, "current_acc": 0.94, "current_lat": 42.0, "current_drift": 1.8, "signals": 15420, "alerts": 2},
        {"name": "FX Hedging Model Monitor", "desc": "Monitoring the foreign exchange hedging recommendation model", "model": "FXHedger_v1", "version": "1.3.0", "interval": 60, "accuracy_thresh": 0.88, "latency_thresh": 100.0, "drift_thresh": 5.0, "current_acc": 0.91, "current_lat": 78.0, "current_drift": 2.1, "signals": 8340, "alerts": 0},
        {"name": "Risk Assessment Monitor", "desc": "Monitoring the portfolio risk assessment and early warning model", "model": "RiskAssessor_v1", "version": "1.0.0", "interval": 120, "accuracy_thresh": 0.85, "latency_thresh": 200.0, "drift_thresh": 7.0, "current_acc": 0.87, "current_lat": 145.0, "current_drift": 4.2, "signals": 4200, "alerts": 1},
    ]
    for m in monitors:
        mon = RegulatoryMonitoring(
            org_id=org_id, monitor_name=m["name"], description=m["desc"],
            status=MonitoringStatus.ACTIVE,
            target_model_name=m["model"], target_model_version=m["version"],
            signal_types=["accuracy", "latency", "drift", "throughput", "feature_importance_shift"],
            sampling_interval_seconds=m["interval"],
            metrics_tracked=["accuracy", "latency", "drift", "throughput", "prediction_distribution"],
            accuracy_threshold=m["accuracy_thresh"], latency_threshold_ms=m["latency_thresh"],
            drift_threshold_pct=m["drift_thresh"],
            current_accuracy=m["current_acc"], current_latency_ms=m["current_lat"],
            current_drift_pct=m["current_drift"],
            total_signals_captured=m["signals"], total_alerts_fired=m["alerts"],
            alert_severity=AlertSeverity.HIGH, auto_escalate=True,
            alert_contacts=[{"name": "Risk Team", "email": "risk@quantive.com"}, {"name": "CTO", "email": "cto@quantive.com"}],
        )
        session.add(mon)
        mon_count += 1
    session.flush()

    # ── Cybersecurity Controls ──
    controls = [
        {"name": "AES-256 Data Encryption at Rest", "type": SecurityControlType.ENCRYPTION_AT_REST, "algo": "AES-256-GCM", "key_len": 256, "key_rot": 90, "adversarial_freq": "monthly", "adversarial_score": 92.0, "attacks": ["data_extraction", "model_stealing"], "integrity": True, "supply_chain": True, "sandbox": True, "frameworks": ["NIST SP 800-57", "ISO 27001"], "vulns": 0, "remediated": 0, "mttr": 0, "score": 98},
        {"name": "TLS 1.3 Transit Encryption", "type": SecurityControlType.ENCRYPTION_IN_TRANSIT, "algo": "TLS 1.3", "key_len": 256, "key_rot": 30, "adversarial_freq": "weekly", "adversarial_score": 95.0, "attacks": ["mitm", "downgrade"], "integrity": True, "supply_chain": False, "sandbox": False, "frameworks": ["PCI DSS", "SOC 2"], "vulns": 0, "remediated": 0, "mttr": 0, "score": 99},
        {"name": "Adversarial ML Defense", "type": SecurityControlType.ADVERSARIAL_DEFENSE, "algo": "FGSM Defense + PGD Training", "key_len": None, "key_rot": None, "adversarial_freq": "daily", "adversarial_score": 87.5, "attacks": ["fgsm", "pgd", "cw", "deepfool", "backdoor"], "integrity": True, "supply_chain": True, "sandbox": True, "frameworks": ["NIST AI RMF", "MITRE ATLAS"], "vulns": 2, "remediated": 2, "mttr": 4.5, "score": 91},
        {"name": "Model Integrity Verification", "type": SecurityControlType.MODEL_SAFETY, "algo": "SHA-3-512 Hash Chain + Digital Signatures", "key_len": 512, "key_rot": 14, "adversarial_freq": "daily", "adversarial_score": 94.0, "attacks": ["model_tampering", "supply_chain_poisoning"], "integrity": True, "supply_chain": True, "sandbox": True, "frameworks": ["EU AI Act", "ISO 42001"], "vulns": 1, "remediated": 1, "mttr": 2.0, "score": 96},
        {"name": "HSM Key Management", "type": SecurityControlType.KEY_MANAGEMENT, "algo": "RSA-4096 + ECC P-384", "key_len": 4096, "key_rot": 365, "adversarial_freq": "quarterly", "adversarial_score": 99.0, "attacks": ["key_theft", "side_channel"], "integrity": True, "supply_chain": False, "sandbox": False, "frameworks": ["FIPS 140-3", "Common Criteria EAL4+"], "vulns": 0, "remediated": 0, "mttr": 0, "score": 99},
        {"name": "Zero Trust Network Access", "type": SecurityControlType.ACCESS_CONTROL, "algo": "mTLS + OIDC + RBAC", "key_len": 256, "key_rot": 7, "adversarial_freq": "continuous", "adversarial_score": 93.0, "attacks": ["privilege_escalation", "lateral_movement"], "integrity": True, "supply_chain": True, "sandbox": False, "frameworks": ["NIST SP 800-207", "SOC 2 Type II"], "vulns": 1, "remediated": 1, "mttr": 1.0, "score": 95},
    ]
    for c in controls:
        ctrl = CybersecurityControl(
            org_id=org_id, control_name=c["name"], control_type=c["type"],
            description=f"Production {c['name'].lower()} for AI trading platform",
            status=SecurityStatus.COMPLIANT,
            encryption_algorithm=c["algo"], key_length_bits=c["key_len"],
            key_rotation_days=c["key_rot"],
            adversarial_testing_frequency=c["adversarial_freq"],
            adversarial_robustness_score=c["adversarial_score"],
            attack_types_defended=c["attacks"],
            model_integrity_verification=c["integrity"],
            supply_chain_scanning=c["supply_chain"],
            sandbox_execution=c["sandbox"],
            framework_references=c["frameworks"],
            vulnerabilities_found=c["vulns"], vulnerabilities_remediated=c["remediated"],
            mean_time_to_remediate_hours=c["mttr"], security_score=c["score"],
        )
        session.add(ctrl)
        sec_count += 1
    session.flush()

    # ── Data Privacy Compliance ──
    policies = [
        {"name": "GDPR Data Protection Policy", "framework": PrivacyFramework.GDPR, "desc": "EU General Data Protection Regulation compliance for sovereign debt data", "data_types": ["government_financial_data", "trading_signals", "portfolio_positions", "risk_metrics"], "classification": DataClassification.RESTRICTED, "jurisdictions": ["EU", "UK", "EEA"], "encrypt": True, "anonymize": False, "pseudo": True, "retention": 2555, "erasure": True, "portability": True, "consent": True, "breach_hours": 72, "breach_auth": ["ICO", "CNIL", "BaFin"], "dpia": True, "dpo": "Dr. Maria Schmidt", "compliant": True, "score": 96},
        {"name": "SEC Customer Data Privacy", "framework": PrivacyFramework.CCPA, "desc": "US SEC and CCPA privacy requirements for broker integration data", "data_types": ["customer_pii", "account_data", "transaction_history", "kyc_documents"], "classification": DataClassification.CONFIDENTIAL, "jurisdictions": ["US", "California", "New York"], "encrypt": True, "anonymize": True, "pseudo": False, "retention": 1095, "erasure": True, "portability": True, "consent": True, "breach_hours": 72, "breach_auth": ["SEC", "State AG"], "dpia": False, "dpo": "James Wilson, CISO", "compliant": True, "score": 91},
        {"name": "Multi-Jurisdiction Data Residency", "framework": PrivacyFramework.CUSTOM, "desc": "Cross-border data residency and transfer controls for international exchanges", "data_types": ["trading_data", "settlement_records", "compliance_logs", "audit_trails"], "classification": DataClassification.CONFIDENTIAL, "jurisdictions": ["US", "EU", "UK", "Singapore", "Japan"], "encrypt": True, "anonymize": False, "pseudo": True, "retention": 2190, "erasure": False, "portability": True, "consent": True, "breach_hours": 48, "breach_auth": ["Multiple DPAs"], "dpia": True, "dpo": "Legal & Compliance Team", "compliant": True, "score": 88},
    ]
    for p in policies:
        pri = DataPrivacyCompliance(
            org_id=org_id, policy_name=p["name"], framework=p["framework"],
            description=p["desc"], data_types=p["data_types"],
            data_classification=p["classification"], jurisdictions=p["jurisdictions"],
            encryption_required=p["encrypt"], anonymization_required=p["anonymize"],
            pseudonymization_required=p["pseudo"], data_retention_days=p["retention"],
            right_to_erasure=p["erasure"], data_portability=p["portability"],
            consent_management=p["consent"], breach_notification_hours=p["breach_hours"],
            breach_notification_authorities=p["breach_auth"],
            breach_response_plan=True, is_compliant=p["compliant"],
            dpia_completed=p["dpia"], dpo_name=p["dpo"],
            data_subject_requests=47, breach_incidents=0, privacy_score=p["score"],
        )
        session.add(pri)
        pri_count += 1
    session.flush()

    # ── Interoperability Standards ──
    standards = [
        {"name": "FIX Protocol 5.0 SP2", "framework": InteroperabilityFramework.FIX_PROTOCOL, "desc": "Financial Information eXchange protocol for real-time order routing with NYSE and regional exchanges", "jurisdictions": ["US", "EU"], "assets": ["treasury_bonds", "sovereign_debt"], "venues": ["NYSE", "NASDAQ", "CME"], "aml": "OFAC SDN + FinCEN CTR", "settlement": ["DTC", "Fedwire"], "status": ComplianceStandardStatus.SUPPORTED, "compat": 97.5, "messages": 125000, "error": 0.02},
        {"name": "ISO 20022 Cross-Border", "framework": InteroperabilityFramework.ISO_20022, "desc": "ISO 20022 messaging standard for cross-border sovereign debt settlement", "jurisdictions": ["Global"], "assets": ["government_bonds", "sovereign_securities"], "venues": ["SWIFT", "TARGET2", "CIPS"], "aml": "FATF Travel Rule", "settlement": ["SWIFT gpi", "CLS", "CIPS"], "status": ComplianceStandardStatus.SUPPORTED, "compat": 94.2, "messages": 89000, "error": 0.08},
        {"name": "REST API Gateway v3", "framework": InteroperabilityFramework.REST_API, "desc": "RESTful API for crypto exchange integration with rate limiting and versioning", "jurisdictions": ["Global"], "assets": ["crypto_sovereign_tokens", "stablecoins"], "venues": ["Coinbase", "Binance", "Kraken"], "aml": "Travel Rule + Chainalysis", "settlement": ["USDC", "USDT", "BTC"], "status": ComplianceStandardStatus.SUPPORTED, "compat": 99.1, "messages": 340000, "error": 0.01},
        {"name": "SWIFT MT/MX Migration", "framework": InteroperabilityFramework.SWIFT_MESSAGING, "desc": "SWIFT MT to MX (ISO 20022) migration for legacy broker integration", "jurisdictions": ["Global"], "assets": ["all_fi_assets"], "venues": ["All SWIFT members"], "aml": "SWIFT CPD + KYC Registry", "settlement": ["SWIFT", "RTGS"], "status": ComplianceStandardStatus.PARTIAL, "compat": 78.0, "messages": 52000, "error": 0.15},
        {"name": "Blockchain Settlement Layer", "framework": InteroperabilityFramework.BLOCKCHAIN, "desc": "Hyperledger Fabric private blockchain for immutable settlement audit trail", "jurisdictions": ["Global"], "assets": ["tokenized_sovereign_debt", "digital_bonds"], "venues": ["Private consortium"], "aml": "On-chain KYC + Oracle verification", "settlement": ["Atomic swap", "HTLC"], "status": ComplianceStandardStatus.SUPPORTED, "compat": 91.0, "messages": 18000, "error": 0.05},
    ]
    for s in standards:
        std = InteroperabilityStandard(
            org_id=org_id, standard_name=s["name"], framework=s["framework"],
            description=s["desc"], jurisdictions=s["jurisdictions"],
            asset_types=s["assets"], exchange_venues=s["venues"],
            aml_kyc_standard=s["aml"], settlement_systems=s["settlement"],
            status=s["status"], compatibility_score=s["compat"],
            messages_processed=s["messages"], error_rate_pct=s["error"],
        )
        session.add(std)
        int_count += 1
    session.flush()

    session.commit()
    print(f"  Created {mon_count} monitors, {sec_count} cybersecurity controls, {pri_count} privacy policies, {int_count} interoperability standards")


# ── Section 12: Independent Validation & Vendor Risk ──────────────────

def seed_validation_vendor(session, org_id):
    print()
    print("[12/12] Seeding independent validation & vendor risk data...")

    val_count = ven_count = 0

    # ── Independent Validations ──
    validations = [
        {"name": "DebtOptimizer v2.1 Backtest", "type": ValidationType.BACKTESTING, "model": "DebtOptimizer", "version": "2.1.0", "desc": "Full backtest of sovereign debt optimization model on 5 years of historical data", "status": ValStatus.PASSED, "ois_sharpe": 1.82, "is_sharpe": 2.14, "ois_ret": 14.2, "is_ret": 16.8, "max_dd": 8.3, "calmar": 1.71, "sortino": 2.45, "info_ratio": 1.32, "degrad_sharpe": 14.7, "degrad_ret": 15.5, "champion": True, "challenger": False, "sign_off": "Dr. Elena Vasquez", "role": SignOffRole.CRO, "findings": ["Model shows consistent alpha generation across all regimes", "Slight degradation in high-volatility periods (< 15%)"], "recs": ["Increase training window for regime detection", "Add momentum features for crisis periods"]},
        {"name": "FXHedger v1.3 Champion/Challenger", "type": ValidationType.CHAMPION_CHALLENGER, "model": "FXHedger", "version": "1.3.0", "desc": "Champion vs challenger comparison for FX hedging model", "status": ValStatus.PASSED, "ois_sharpe": 1.45, "is_sharpe": 1.62, "ois_ret": 9.8, "is_ret": 11.2, "max_dd": 6.1, "calmar": 1.61, "sortino": 2.11, "info_ratio": 1.08, "degrad_sharpe": 10.3, "degrad_ret": 12.8, "champion": False, "challenger": True, "sign_off": "James Wilson", "role": SignOffRole.CTO, "findings": ["Challenger model outperforms champion by 12% on risk-adjusted basis", "Better performance in USD/EUR and USD/GBP pairs"], "recs": ["Promote challenger to champion after 30-day parallel run", "Monitor for overfitting in emerging market pairs"]},
        {"name": "RiskAssessor v1.0 Monte Carlo", "type": ValidationType.MONTE_CARLO, "model": "RiskAssessor", "version": "1.0.0", "desc": "Monte Carlo simulation for portfolio risk assessment model", "status": ValStatus.PASSED, "ois_sharpe": 1.28, "is_sharpe": 1.41, "ois_ret": 8.5, "is_ret": 9.7, "max_dd": 11.2, "calmar": 0.87, "sortino": 1.89, "info_ratio": 0.94, "degrad_sharpe": 9.4, "degrad_ret": 12.4, "champion": False, "challenger": False, "sign_off": "Risk Committee", "role": SignOffRole.RISK_COMMITTEE, "findings": ["VaR estimates within 95% confidence band", "CVR(95) = $4.2M, CVR(99) = $6.8M"], "recs": ["Increase simulation count to 10,000", "Add regime-conditional correlation modeling"]},
        {"name": "PortfolioRebalancer v2.0 Walk-Forward", "type": ValidationType.WALK_FORWARD, "model": "PortfolioRebalancer", "version": "2.0.0", "desc": "Walk-forward validation with rolling 6-month windows", "status": ValStatus.IN_PROGRESS, "ois_sharpe": 1.55, "is_sharpe": None, "ois_ret": 11.3, "is_ret": None, "max_dd": 7.8, "calmar": 1.45, "sortino": 2.02, "info_ratio": 1.15, "degrad_sharpe": None, "degrad_ret": None, "champion": False, "challenger": False, "sign_off": None, "role": None, "findings": None, "recs": None},
        {"name": "EarlyWarning v1.2 Robustness", "type": ValidationType.ROBUSTNESS, "model": "EarlyWarning", "version": "1.2.0", "desc": "Robustness testing across stress scenarios and edge cases", "status": ValStatus.CONDITIONAL, "ois_sharpe": 1.12, "is_sharpe": 1.35, "ois_ret": 7.2, "is_ret": 8.9, "max_dd": 14.5, "calmar": 0.61, "sortino": 1.56, "info_ratio": 0.78, "degrad_sharpe": 17.2, "degrad_ret": 19.4, "champion": False, "challenger": False, "sign_off": "Dr. Elena Vasquez", "role": SignOffRole.CRO, "findings": ["Model degrades in extreme tail events", "Parameter sensitivity high for interest rate feature"], "recs": ["Retrain with expanded crisis dataset", "Add robustness constraints to optimization"], "conditions": ["Must complete stress test expansion before production", "Add regime detection module"]},
    ]
    for v in validations:
        iv = IndependentValidation(
            org_id=org_id, validation_name=v["name"], validation_type=v["type"],
            model_name=v["model"], model_version=v["version"], description=v["desc"],
            status=v["status"],
            backtest_start_date=datetime(2021, 1, 1, tzinfo=timezone.utc),
            backtest_end_date=datetime(2025, 12, 31, tzinfo=timezone.utc),
            backtest_period_days=1826, in_sample_pct=70.0, out_of_sample_pct=30.0,
            in_sample_sharpe=v["is_sharpe"], out_of_sample_sharpe=v["ois_sharpe"],
            in_sample_return_pct=v["is_ret"], out_of_sample_return_pct=v["ois_ret"],
            max_drawdown_pct=v["max_dd"], calmar_ratio=v["calmar"],
            sortino_ratio=v["sortino"], information_ratio=v["info_ratio"],
            sharpe_degradation_pct=v["degrad_sharpe"], return_degradation_pct=v["degrad_ret"],
            max_acceptable_degradation_pct=20.0,
            is_champion=v["champion"], is_challenger=v["challenger"],
            sign_off_by=v["sign_off"], sign_off_role=v["role"],
            sign_off_date=datetime.now(timezone.utc) if v["sign_off"] else None,
            findings=v["findings"], recommendations=v["recs"],
            conditions=v.get("conditions"),
            next_validation_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
            monte_carlo_simulations=5000 if v["type"] == ValidationType.MONTE_CARLO else None,
            monte_carlo_confidence_interval=95.0 if v["type"] == ValidationType.MONTE_CARLO else None,
            monte_carlo_var_95=4200000.0 if v["type"] == ValidationType.MONTE_CARLO else None,
            monte_carlo_var_99=6800000.0 if v["type"] == ValidationType.MONTE_CARLO else None,
            regime_changes_tested=["2020_covid", "2022_rate_hikes", "2023_banking_crisis"] if v["type"] == ValidationType.ROBUSTNESS else None,
            edge_cases_tested=["flash_crash", "liquidity_crisis", "correlated_defaults"] if v["type"] == ValidationType.ROBUSTNESS else None,
        )
        session.add(iv)
        val_count += 1
    session.flush()

    # ── Vendor Risk Assessments ──
    vendors = [
        {"name": "Bloomberg LP", "cat": VendorCategory.MARKET_DATA, "crit": VendorCriticality.CRITICAL, "status": VendorStatus.ACTIVE, "desc": "Real-time market data, pricing, and analytics feed", "annual": 480000, "dd_score": 94, "soc2": True, "iso27001": True, "uptime": 99.99, "sla_breach": 0, "overall": 12, "security": 8, "operational": 10, "compliance": 15, "financial": 10, "incidents": 0, "esc": 0, "sub": ["AWS us-east-1", "Bloomberg Data Center"], "fourth": True, "data_share": True, "irp": True, "bcp": True, "rto": 2, "gdpr": True, "ccpa": True, "sanctions": True, "aml": True},
        {"name": "Amazon Web Services", "cat": VendorCategory.CLOUD_INFRASTRUCTURE, "crit": VendorCriticality.CRITICAL, "status": VendorStatus.ACTIVE, "desc": "Cloud infrastructure for all AI model hosting and inference", "annual": 320000, "dd_score": 97, "soc2": True, "iso27001": True, "uptime": 99.999, "sla_breach": 0, "overall": 8, "security": 5, "operational": 8, "compliance": 10, "financial": 5, "incidents": 0, "esc": 0, "sub": ["Cloudflare", "Fastly"], "fourth": True, "data_share": True, "irp": True, "bcp": True, "rto": 0.5, "gdpr": True, "ccpa": True, "sanctions": True, "aml": False},
        {"name": "State Street Corporation", "cat": VendorCategory.CUSTODIAN, "crit": VendorCriticality.CRITICAL, "status": VendorStatus.ACTIVE, "desc": "Global custodian for sovereign debt portfolio securities", "annual": 180000, "dd_score": 91, "soc2": True, "iso27001": True, "uptime": 99.97, "sla_breach": 1, "overall": 15, "security": 12, "operational": 14, "compliance": 18, "financial": 12, "incidents": 1, "esc": 0, "sub": ["DTCC", "Fedwire"], "fourth": True, "data_share": True, "irp": True, "bcp": True, "rto": 4, "gdpr": True, "ccpa": True, "sanctions": True, "aml": True},
        {"name": "Coinbase Institutional", "cat": VendorCategory.EXCHANGE, "crit": VendorCriticality.HIGH, "status": VendorStatus.ACTIVE, "desc": "Crypto exchange for tokenized sovereign debt and digital asset trading", "annual": 85000, "dd_score": 86, "soc2": True, "iso27001": False, "uptime": 99.95, "sla_breach": 2, "overall": 28, "security": 22, "operational": 25, "compliance": 30, "financial": 20, "incidents": 2, "esc": 1, "sub": ["AWS us-west-2"], "fourth": False, "data_share": True, "irp": True, "bcp": True, "rto": 1, "gdpr": True, "ccpa": True, "sanctions": True, "aml": True},
        {"name": "Chainalysis", "cat": VendorCategory.KYC_AML, "crit": VendorCriticality.HIGH, "status": VendorStatus.ACTIVE, "desc": "Blockchain analytics and KYC/AML compliance for crypto transactions", "annual": 65000, "dd_score": 89, "soc2": True, "iso27001": True, "uptime": 99.98, "sla_breach": 0, "overall": 18, "security": 15, "operational": 18, "compliance": 20, "financial": 15, "incidents": 0, "esc": 0, "sub": ["Google Cloud"], "fourth": False, "data_share": True, "irp": True, "bcp": True, "rto": 1, "gdpr": True, "ccpa": True, "sanctions": True, "aml": True},
        {"name": "CrowdStrike", "cat": VendorCategory.CYBERSECURITY, "crit": VendorCriticality.HIGH, "status": VendorStatus.ACTIVE, "desc": "Endpoint detection, threat intelligence, and incident response", "annual": 42000, "dd_score": 92, "soc2": True, "iso27001": True, "uptime": 99.99, "sla_breach": 0, "overall": 10, "security": 8, "operational": 10, "compliance": 12, "financial": 8, "incidents": 0, "esc": 0, "sub": [], "fourth": False, "data_share": True, "irp": True, "bcp": True, "rto": 0.5, "gdpr": True, "ccpa": True, "sanctions": False, "aml": False},
        {"name": "Deloitte Advisory", "cat": VendorCategory.AUDIT, "crit": VendorCriticality.MEDIUM, "status": VendorStatus.ACTIVE, "desc": "External auditor for SOC 2 Type II and algorithmic validation", "annual": 120000, "dd_score": 95, "soc2": True, "iso27001": True, "uptime": None, "sla_breach": 0, "overall": 14, "security": 10, "operational": 12, "compliance": 15, "financial": 10, "incidents": 0, "esc": 0, "sub": [], "fourth": False, "data_share": True, "irp": True, "bcp": True, "rto": None, "gdpr": True, "ccpa": True, "sanctions": True, "aml": True},
        {"name": "LSEG (London Stock Exchange Group)", "cat": VendorCategory.MARKET_DATA, "crit": VendorCriticality.MEDIUM, "status": VendorStatus.ACTIVE, "desc": "European market data and post-trade services for gilt and bund trading", "annual": 95000, "dd_score": 88, "soc2": True, "iso27001": True, "uptime": 99.96, "sla_breach": 1, "overall": 22, "security": 18, "operational": 20, "compliance": 25, "financial": 18, "incidents": 1, "esc": 0, "sub": ["Azure UK South"], "fourth": False, "data_share": True, "irp": True, "bcp": True, "rto": 2, "gdpr": True, "ccpa": False, "sanctions": True, "aml": True},
        {"name": "Refinitiv (LSEG)", "cat": VendorCategory.MARKET_DATA, "crit": VendorCriticality.MEDIUM, "status": VendorStatus.ACTIVE, "desc": "FX and fixed income pricing data for sovereign bond valuation", "annual": 72000, "dd_score": 87, "soc2": True, "iso27001": True, "uptime": 99.94, "sla_breach": 2, "overall": 25, "security": 20, "operational": 22, "compliance": 28, "financial": 22, "incidents": 2, "esc": 1, "sub": ["AWS eu-west-1"], "fourth": False, "data_share": True, "irp": True, "bcp": True, "rto": 3, "gdpr": True, "ccpa": True, "sanctions": True, "aml": True},
        {"name": "Palantir Foundry", "cat": VendorCategory.OTHER, "crit": VendorCriticality.LOW, "status": VendorStatus.ACTIVE, "desc": "Data integration and analytics platform for government data pipelines", "annual": 55000, "dd_score": 83, "soc2": True, "iso27001": False, "uptime": 99.92, "sla_breach": 3, "overall": 35, "security": 28, "operational": 32, "compliance": 38, "financial": 25, "incidents": 3, "esc": 2, "sub": ["Azure Government"], "fourth": False, "data_share": True, "irp": True, "bcp": True, "rto": 4, "gdpr": True, "ccpa": True, "sanctions": True, "aml": False},
    ]
    for v in vendors:
        vr = VendorRiskAssessment(
            org_id=org_id, vendor_name=v["name"], vendor_category=v["cat"],
            description=v["desc"], status=v["status"], criticality=v["crit"],
            annual_spend_usd=v["annual"],
            due_diligence_completed=True, due_diligence_date=datetime(2025, 6, 15, tzinfo=timezone.utc),
            due_diligence_score=v["dd_score"], background_check=True,
            financial_stability_check=True, regulatory_status_check=True,
            soc2_type_ii=v["soc2"], iso27001_certified=v["iso27001"],
            sla_uptime_pct=99.99, actual_uptime_pct=v["uptime"],
            sla_breaches_ytd=v["sla_breach"],
            overall_risk_score=v["overall"], security_risk_score=v["security"],
            operational_risk_score=v["operational"], compliance_risk_score=v["compliance"],
            financial_risk_score=v["financial"],
            sub_processors=v["sub"], fourth_party_risk=v["fourth"],
            data_sharing_agreement=v["data_share"],
            incident_response_plan=v["irp"], business_continuity_plan=v["bcp"],
            disaster_recovery_rto_hours=v["rto"],
            gdpr_compliant=v["gdpr"], ccpa_compliant=v["ccpa"],
            sanctions_screening=v["sanctions"], amil_kyc_compliant=v["aml"],
            incidents_ytd=v["incidents"], escalations_ytd=v["esc"],
            last_review_date=datetime(2025, 9, 1, tzinfo=timezone.utc),
            next_review_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
            review_frequency="quarterly",
        )
        session.add(vr)
        ven_count += 1
    session.flush()

    session.commit()
    print(f"  Created {val_count} validations, {ven_count} vendor risk assessments")


# ── Main ──────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("QUANTIVE — COMPREHENSIVE SEED SCRIPT")
    print("=" * 60)
    print()

    # Create all tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")
    print()

    session = SessionLocal()

    try:
        org_id, user_id, portfolio_id = seed_org_and_user(session)
        seed_pfm(session, org_id)
        seed_ai_governance(session, org_id)
        seed_exchange_integration(session, org_id)
        seed_broker_integration(session, org_id)
        seed_regulatory_compliance(session, org_id)
        seed_exchange_due_diligence(session, org_id)
        seed_cybersecurity_privacy(session, org_id)
        seed_validation_vendor(session, org_id)

        print()
        print("=" * 60)
        print("SEED COMPLETE!")
        print("=" * 60)
        print()
        print("Summary:")
        print(f"  Organization: {org_id}")
        print(f"  User: demo@quantive.com")
        print(f"  Portfolio: {portfolio_id}")
        print()
        print("Access the platform:")
        print("  Frontend: http://localhost:5173")
        print("  Backend:  http://localhost:8000")
        print()
        print("Pages to visit:")
        print("  /pfm-import         — PFM Data Import")
        print("  /ai-governance      — AI Governance Framework")
        print("  /exchange-integration — Exchange Integration")
        print("  /broker-integration — Broker Integration")
        print("  /regulatory-compliance — Regulatory Compliance")
        print("  /validation-vendor-risk — Validation & Vendor Risk")

    except Exception as e:
        session.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
