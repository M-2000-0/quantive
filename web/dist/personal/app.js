/* Quantive Personal — static demo engine. No server: state in localStorage.
   Mirrors backend/app/personal (questions, packs, detect, scoring, caps). */
(function () {
  'use strict';

  var KEY = 'qp_state_v1';

  /* ── 24-question adaptive onboarding (mirrors onboarding_questions.py) ── */
  var QUESTIONS = [
    { id: 'income_sources', group: 'income', prompt: 'How do you currently earn money?', kind: 'multi', options: ['employment', 'business', 'freelance', 'investments', 'rental', 'other'] },
    { id: 'employment_detail', group: 'income', prompt: 'Are you employed by a company or organization?', kind: 'single', options: ['yes', 'no'], requires: { fact: 'income_sources', has: 'employment' } },
    { id: 'business_detail', group: 'income', prompt: 'Do you own or operate a business?', kind: 'single', options: ['yes', 'no'], requires: { fact: 'income_sources', has: 'business' } },
    { id: 'freelance_detail', group: 'income', prompt: 'Do you do freelance or independent work?', kind: 'single', options: ['yes', 'no'], requires: { fact: 'income_sources', has: 'freelance' } },
    { id: 'investment_income', group: 'income', prompt: 'Do you receive investment income (dividends, interest, gains)?', kind: 'single', options: ['yes', 'no'] },
    { id: 'rental_income', group: 'income', prompt: 'Do you receive rental income?', kind: 'single', options: ['yes', 'no'] },
    { id: 'housing', group: 'housing', prompt: 'What best describes your housing?', kind: 'multi', options: ['rent', 'own', 'mortgage', 'rental_property', 'primary_residence'] },
    { id: 'mortgage_detail', group: 'housing', prompt: 'Do you pay mortgage interest?', kind: 'single', options: ['yes', 'no'], requires: { fact: 'housing', has: 'mortgage' } },
    { id: 'work_home', group: 'work', prompt: 'Do you work from home?', kind: 'single', options: ['yes', 'no', 'sometimes'] },
    { id: 'home_office', group: 'work', prompt: 'Do you have a dedicated home office space?', kind: 'single', options: ['yes', 'no'], requires: { fact: 'work_home', hasAny: ['yes', 'sometimes'] } },
    { id: 'work_expenses', group: 'work', prompt: 'Do you pay for work equipment or professional expenses?', kind: 'single', options: ['yes', 'no'] },
    { id: 'family', group: 'family', prompt: 'Do you have a spouse/partner or dependents?', kind: 'multi', options: ['spouse', 'children', 'dependents', 'none'] },
    { id: 'dependents_count', group: 'family', prompt: 'How many dependents?', kind: 'single', options: ['0', '1', '2', '3+'], requires: { fact: 'family', hasAny: ['children', 'dependents'] } },
    { id: 'education_exp', group: 'family', prompt: 'Did you pay education expenses (you or dependents)?', kind: 'single', options: ['yes', 'no'] },
    { id: 'medical_exp', group: 'health', prompt: 'Did you pay medical, dental, or vision expenses?', kind: 'single', options: ['yes', 'no'] },
    { id: 'health_insurance', group: 'health', prompt: 'Do you pay health insurance premiums?', kind: 'single', options: ['yes', 'no'] },
    { id: 'retirement', group: 'financial', prompt: 'Do you contribute to a retirement account?', kind: 'single', options: ['yes', 'no'] },
    { id: 'invest_accounts', group: 'financial', prompt: 'Do you hold investment or brokerage accounts?', kind: 'single', options: ['yes', 'no'] },
    { id: 'donations', group: 'financial', prompt: 'Did you make charitable donations?', kind: 'single', options: ['yes', 'no'] },
    { id: 'loans', group: 'financial', prompt: 'Do you pay interest on loans (non-mortgage)?', kind: 'single', options: ['yes', 'no'] },
    { id: 'country', group: 'tax', prompt: 'What is your country of tax residence?', kind: 'single', options: ['MX', 'US', 'BD', 'other'] },
    { id: 'tax_regime', group: 'tax', prompt: 'Do you know your applicable tax regime?', kind: 'single', options: ['yes', 'no', 'needs_confirmation'] },
    { id: 'filing_status', group: 'tax', prompt: 'What is your filing status?', kind: 'single', options: ['single', 'married', 'other', 'unknown'] },
    { id: 'docs_ready', group: 'tax', prompt: 'Do you have income/housing/medical documents ready to organize?', kind: 'single', options: ['yes', 'some', 'no'] }
  ];

  /* ── Plans (mirrors billing.py) ── */
  var PLANS = [
    { tier: 'personal_2k', name: 'Starter', price: 2000,
      features: ['Tax write-off detection only', 'Up to 3 opportunities tracked', '10 documents', '20 intelligence questions / month', 'No Gov-grade market access', 'Summary report only'],
      limits: { opportunities: 3, documents: 10, asks: 20, gov: false, fullReport: false } },
    { tier: 'personal', name: 'Personal', price: 5000,
      features: ['Continuous financial profile', 'Year-round tax intelligence', 'Unlimited opportunities + documents', 'Unlimited intelligence', 'Annual intelligence report'],
      limits: { opportunities: -1, documents: -1, asks: -1, gov: false, fullReport: true } },
    { tier: 'personal_10k', name: 'Sovereign', price: 10000,
      features: ['Everything in Personal', 'Gov-grade market access (aggregated Qubo trends)', 'Sovereign-mode insights', 'CPA-ready export'],
      limits: { opportunities: -1, documents: -1, asks: -1, gov: true, fullReport: true } }
  ];

  /* Rule-ref titles + verify notes (mirrors tax_packs.py; full text needs server) */
  var REFS = {
    'MX-2026-mortgage-interest': 'Mexico · mortgage interest — verify against SAT / miscelánea vigente',
    'GEN-2026-medical-expenses': 'General · medical expenses — verify thresholds in your jurisdiction',
    'GEN-2026-retirement': 'General · retirement — verify account type and limits',
    'GEN-2026-education': 'General · education — verify eligibility',
    'GEN-2026-home-office': 'General · home office — verify regime and exclusivity rules',
    'GEN-2026-housing-interest': 'General · housing loan interest — verify loan type and regime',
    'GEN-2026-mortgage-interest': 'General · housing loan interest — verify loan type and regime',
    'GEN-2026-donations': 'General · donations — verify recipient eligibility and receipt rules',
    'US-2026-mortgage-interest': 'US · mortgage interest (Schedule A) — verify against current IRS publications',
    'US-2026-salt': 'US · SALT cap — confirm the current-year cap before assuming anything',
    'US-2026-student-loan-interest': 'US · student loan interest — verify phaseouts and current figures',
    'US-2026-medical-75pct': 'US · medical AGI floor — verify current floor; itemizers only',
    'US-2026-retirement': 'US · 401(k)/IRA — verify limits and deductibility phaseouts',
    'US-2026-charitable': 'US · charitable — verify AGI limits and substantiation rules',
    'US-2026-home-office': 'US · home office — verify exclusive-use test and method',
    'BD-2026-investment-rebate': 'Bangladesh · investment rebate — verify NBR / Finance Act schedule',
    'BD-2026-hra': 'Bangladesh · house rent allowance — verify current exemption formula',
    'BD-2026-savings-instruments': 'Bangladesh · savings instruments — verify current NBR circulars',
    'BD-2026-rental-income': 'Bangladesh · rental deductions — verify allowable items'
  };

  var GOV_TRENDS = [
    { segment: '25–34', signal: 'investing more in diversified instruments', direction: 'up' },
    { segment: '35–44', signal: 'spending more on housing-related costs', direction: 'up' },
    { segment: '45–54', signal: 'allocating more toward retirement contributions', direction: 'flat' }
  ];

  /* ── Store ── */
  function blank() {
    return { plan: 'personal_2k', answers: {}, reviews: {}, docs: [], asks: [], tasksClosed: [], onboarded: false, seq: 1 };
  }
  function load() {
    try {
      var raw = localStorage.getItem(KEY);
      if (!raw) return blank();
      var s = JSON.parse(raw);
      if (!s || typeof s !== 'object' || !s.answers) return blank();
      s.reviews = s.reviews || {}; s.docs = s.docs || []; s.asks = s.asks || [];
      s.tasksClosed = s.tasksClosed || []; s.seq = s.seq || 1;
      if (!planOf(s.plan)) s.plan = 'personal_2k';
      return s;
    } catch (e) { return blank(); }
  }
  function save(s) { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) {} }
  function reset() { try { localStorage.removeItem(KEY); } catch (e) {} }

  function planOf(tier) { return PLANS.filter(function (p) { return p.tier === tier; })[0] || null; }
  function limitsOf(state) { return planOf(state.plan).limits; }

  /* ── Helpers ── */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function norm(a) { return Array.isArray(a) ? a.map(String) : (a == null || a === '' ? [] : [String(a)]); }
  function has(ans, key, val) { return norm(ans[key]).indexOf(val) !== -1; }
  function normalizeCountry(v) {
    v = String(v || '').toUpperCase();
    return (v === 'MX' || v === 'US' || v === 'BD') ? v : 'GEN';
  }
  function jurisOf(answers) {
    var c = norm(answers.country)[0] || '';
    return normalizeCountry(c);
  }
  function refFor(juris) {
    var want = Array.prototype.slice.call(arguments, 1);
    for (var i = 0; i < want.length; i++) if (want[i].indexOf(juris + '-') === 0) return [want[i]];
    for (var j = 0; j < want.length; j++) if (want[j].indexOf('GEN-') === 0) return [want[j]];
    return [want[0]];
  }

  function visibleQuestions(answers) {
    return QUESTIONS.filter(function (q) {
      var r = q.requires;
      if (!r) return true;
      var prev = norm(answers[r.fact]);
      if (r.has) return prev.indexOf(r.has) !== -1;
      if (r.hasAny) return r.hasAny.some(function (v) { return prev.indexOf(v) !== -1; });
      return true;
    });
  }

  /* ── Opportunity detector (mirrors opportunity_engine.py) ── */
  function detect(state) {
    var ans = state.answers, juris = jurisOf(ans), tier = state.plan, out = [];
    function add(o) {
      var rev = state.reviews[o.title];
      if (rev === 'dismissed') return;
      o.status = rev === 'not_applicable' ? 'not_applicable' : (rev === 'reviewed' ? 'reviewed' : 'potentially_relevant');
      out.push(o);
    }
    if (has(ans, 'housing', 'mortgage') || has(ans, 'mortgage_detail', 'yes'))
      add({ title: 'Mortgage interest', category: 'housing', relevance: 'high', why: 'You indicated that you have a mortgage.', needs: ['Applicable tax regime', 'Annual mortgage documentation'], refs: refFor(juris, juris + '-2026-mortgage-interest', 'US-2026-mortgage-interest', 'MX-2026-mortgage-interest', 'GEN-2026-housing-interest'), next: 'Upload annual mortgage statement, then confirm regime.' });
    if (has(ans, 'medical_exp', 'yes'))
      add({ title: 'Medical expenses', category: 'health', relevance: 'medium', why: 'You reported qualifying medical expenses.', needs: ['Expense breakdown by category', 'Receipts'], refs: refFor(juris, juris + '-2026-medical-75pct', 'GEN-2026-medical-expenses'), next: 'Organize receipts in Document Center.' });
    if (has(ans, 'retirement', 'yes'))
      add({ title: 'Retirement contributions', category: 'retirement', relevance: 'medium', why: 'You contribute to a retirement account.', needs: ['Account type', 'Annual contributions'], refs: refFor(juris, juris + '-2026-retirement', 'GEN-2026-retirement'), next: 'Confirm account type and totals.' });
    if (has(ans, 'education_exp', 'yes')) {
      if (juris === 'US' && has(ans, 'loans', 'yes'))
        add({ title: 'Student loan interest', category: 'education', relevance: 'medium', why: 'You reported education expenses and loan interest.', needs: ['Eligible loan', 'Income range'], refs: ['US-2026-student-loan-interest'], next: 'Confirm loan eligibility and income phaseout.' });
      else
        add({ title: 'Education expenses', category: 'education', relevance: 'low', why: 'You reported education expenses.', needs: ['Eligible recipient', 'Institution type'], refs: ['GEN-2026-education'], next: 'Confirm eligibility before any conclusion.' });
    } else if (juris === 'US' && has(ans, 'loans', 'yes')) {
      add({ title: 'Student loan interest', category: 'education', relevance: 'medium', why: 'You pay interest on loans.', needs: ['Whether the loan is an eligible student loan', 'Income range'], refs: ['US-2026-student-loan-interest'], next: 'Confirm this is an eligible student loan.' });
    }
    if (has(ans, 'home_office', 'yes'))
      add({ title: 'Home office', category: 'work', relevance: 'low', why: 'You work from a dedicated home space. Treatment is regime-dependent.', needs: ['Tax regime', 'Exclusive-use evidence'], refs: refFor(juris, juris + '-2026-home-office', 'GEN-2026-home-office'), next: 'Answer 2 regime questions in Intelligence.' });
    if (has(ans, 'donations', 'yes'))
      add({ title: 'Charitable donations', category: 'donations', relevance: juris === 'US' ? 'medium' : 'low', why: 'You made charitable donations.', needs: ['Eligible recipient', 'Whether you itemize (US)'], refs: refFor(juris, juris + '-2026-charitable', 'GEN-2026-donations'), next: 'Gather receipts and confirm recipient eligibility.' });
    if (juris === 'US' && (has(ans, 'employment_detail', 'yes') || has(ans, 'housing', 'own') || has(ans, 'housing', 'mortgage')))
      add({ title: 'State and local taxes (SALT)', category: 'housing', relevance: 'low', why: 'You may pay deductible state/local taxes. The cap must be confirmed for the current year.', needs: ['Whether you itemize', 'Current-year SALT cap'], refs: ['US-2026-salt'], next: 'Confirm the current-year cap before assuming anything.' });
    if (juris === 'BD') {
      if (has(ans, 'employment_detail', 'yes'))
        add({ title: 'House rent allowance', category: 'housing', relevance: 'medium', why: 'You are salaried and may receive house rent allowance.', needs: ['Actual rent paid', 'Salary structure'], refs: ['BD-2026-hra'], next: 'Confirm the current exemption formula.' });
      if (has(ans, 'retirement', 'yes') || has(ans, 'invest_accounts', 'yes') || has(ans, 'donations', 'yes'))
        add({ title: 'Investment tax rebate', category: 'retirement', relevance: 'medium', why: 'You hold investments that may qualify for rebate under the yearly schedule.', needs: ['Investment types', 'Current-year rebate schedule'], refs: ['BD-2026-investment-rebate'], next: "Confirm the current assessment year's schedule." });
      if (has(ans, 'invest_accounts', 'yes'))
        add({ title: 'Savings instruments', category: 'financial', relevance: 'low', why: 'You hold savings/investment instruments with NBR-specific treatment.', needs: ['Instrument types'], refs: ['BD-2026-savings-instruments'], next: 'Verify current NBR circulars.' });
      if (has(ans, 'rental_income', 'yes'))
        add({ title: 'Rental income deductions', category: 'housing', relevance: 'medium', why: 'You receive rental income with potentially allowable deductions.', needs: ['Declared rental income', 'Deductible expenses'], refs: ['BD-2026-rental-income'], next: 'Verify allowable deductions before computing.' });
    }
    if (tier === 'personal_10k') {
      if (has(ans, 'invest_accounts', 'yes') || has(ans, 'investment_income', 'yes'))
        add({ title: 'Qubo trend alignment', category: 'sovereign', relevance: 'medium', why: 'Your investor profile can be compared against aggregated Qubo age-bracket trends.', needs: ['Age bracket confirmation'], refs: [], next: "Open Sovereign view for your bracket's trend." });
      add({ title: 'Sovereign insight briefing', category: 'sovereign', relevance: 'low', why: 'Sovereign tier includes a Gov-grade briefing built from aggregates only.', needs: [], refs: [], next: 'See Gov insights for where brackets like yours are allocating.' });
    }
    return out;
  }

  /* ── Score (mirrors scoring.py) ── */
  function score(state) {
    var vis = visibleQuestions(state.answers);
    var facts = Object.keys(state.answers).filter(function (k) { return norm(state.answers[k]).length > 0; }).length;
    var completeness = vis.length ? Math.min(100, Math.round(100 * facts / vis.length)) : 0;
    var open = tasks(state).filter(function (t) { return t.status === 'open'; }).length;
    var gaps = state.docs.length;
    var s = Math.max(0, Math.min(100, completeness - Math.min(12, open * 2) - Math.min(8, gaps)));
    var msg = s >= 85 ? 'Your profile is in strong shape. A few reviews remain.'
      : s >= 65 ? 'Your profile is mostly complete. Quantive identified several areas that may deserve review.'
      : s >= 35 ? 'Good start. Completing onboarding unlocks more precise intelligence.'
      : "Let's build your financial profile — about 8 minutes.";
    return { score: s, completeness: completeness, open: open, gaps: gaps, message: msg };
  }

  function tasks(state) {
    var t = [
      { id: 't-profile', title: 'Complete tax profile', reason: 'Quantive needs additional information about your situation.', link: 'onboarding.html' },
      { id: 't-facts', title: 'Confirm important profile facts', reason: 'You own your profile — review what Quantive inferred.', link: 'profile.html' }
    ];
    if (state.onboarded) t.push({ id: 't-review', title: 'Review your first opportunities', reason: 'Onboarding complete — confirm what Quantive inferred.', link: 'opportunities.html' });
    return t.map(function (x) {
      x.status = state.tasksClosed.indexOf(x.id) !== -1 ? 'done' : 'open';
      return x;
    });
  }

  function asksUsed(state) {
    var cutoff = Date.now() - 30 * 24 * 3600 * 1000;
    return state.asks.filter(function (t) { return t >= cutoff; }).length;
  }

  /* ── Layout ── */
  var NAV = [
    ['Dashboard', 'index.html'], ['My Profile', 'profile.html'], ['Opportunities', 'opportunities.html'],
    ['Documents', 'documents.html'], ['Intelligence', 'intelligence.html'], ['Sovereign', 'gov.html'],
    ['Reports', 'reports.html'], ['Pricing', 'pricing.html'], ['Onboarding', 'onboarding.html']
  ];
  function layout(active, body) {
    var nav = NAV.map(function (n) {
      return '<a class="qp-nav' + (n[0] === active ? ' active' : '') + '" href="' + n[1] + '">' + n[0] + '</a>';
    }).join('');
    return '<div class="qp-demo">Static demo — everything runs in this browser, no server needed. <a href="../index.html">← Back to landing</a></div>' +
      '<div class="qp-shell"><aside class="qp-side">' +
      '<a class="qp-brand" href="index.html"><span class="qp-mark">Q</span><span><strong>Quantive Personal</strong><small>Tax intelligence</small></span></a>' +
      '<nav>' + nav + '</nav><div class="qp-sep"></div>' +
      '<a class="qp-ghost" href="../index.html">← Quantive home</a>' +
      '<p class="qp-note">Demo data stays on this device. Real billing needs the server.</p>' +
      '</aside><main class="qp-main">' + body + '</main></div>';
  }

  function planBanner(state) {
    var p = planOf(state.plan);
    if (state.plan === 'personal_2k')
      return '<div class="qp-warn mt">Starter ($2k/yr): tax write-offs only — up to 3 opportunities, 10 documents, 20 questions/month, no Gov access. <a href="pricing.html">Compare plans →</a></div>';
    if (state.plan === 'personal_10k')
      return '<p class="qp-muted">Sovereign plan · Gov access on · <a href="gov.html">Sovereign view →</a></p>';
    return '<p class="qp-muted">Personal plan ($5k/yr) · <a href="pricing.html">Manage →</a></p>';
  }

  window.QP = {
    QUESTIONS: QUESTIONS, PLANS: PLANS, REFS: REFS, GOV_TRENDS: GOV_TRENDS,
    load: load, save: save, reset: reset, esc: esc, norm: norm, has: has,
    jurisOf: jurisOf, visibleQuestions: visibleQuestions, detect: detect,
    score: score, tasks: tasks, asksUsed: asksUsed, planOf: planOf,
    limitsOf: limitsOf, layout: layout, planBanner: planBanner
  };
})();
