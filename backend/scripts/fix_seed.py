"""Fix seed_all.py - replace incorrect AI governance section."""
import re

with open('scripts/seed_all.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the old seed_ai_governance function boundaries
start_marker = 'def seed_ai_governance(session, org_id):'
end_marker = 'def seed_exchange_integration(session, org_id):'

start_idx = content.index(start_marker)
end_idx = content.index(end_marker)

new_func = '''def seed_ai_governance(session, org_id):
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


'''

content = content[:start_idx] + new_func + content[end_idx:]

with open('scripts/seed_all.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed seed_ai_governance')
