"""Fix exchange and broker sections of seed_all.py to match actual model schemas."""
import re

with open('scripts/seed_all.py', 'r', encoding='utf-8') as f:
    content = f.read()

# ── Fix Exchange Integration ──────────────────────────────────────
exchange_start = 'def seed_exchange_integration(session, org_id):'
exchange_end = 'def seed_broker_integration(session, org_id):'

s1 = content.index(exchange_start)
e1 = content.index(exchange_end)

new_exchange = '''def seed_exchange_integration(session, org_id):
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
        audit = AlgorithmAuditTrail(
            id=gen_id(), org_id=org_id,
            event_type=etype, event_date=days_ago(1),
            event_description=desc,
            input_data_summary=summary,
            confidence_score=conf,
            execution_time_ms=exec_ms,
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


'''

content = content[:s1] + new_exchange + content[e1:]

# ── Fix Broker Integration ───────────────────────────────────────
broker_start = 'def seed_broker_integration(session, org_id):'
broker_end = '# ── Main'

s2 = content.index(broker_start)
e2 = content.index(broker_end)

new_broker = '''def seed_broker_integration(session, org_id):
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


'''

content = content[:s2] + new_broker + content[e2:]

with open('scripts/seed_all.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed exchange and broker sections')
