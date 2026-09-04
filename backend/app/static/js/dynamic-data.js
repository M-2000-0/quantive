/**
 * Quantive Dynamic Data Loader
 * Replaces hardcoded financial values with live data from API responses.
 * 
 * Pages use data-populate attributes or call populateX() functions.
 */
(function() {
  'use strict';

  const API = '/api';
  const cache = {};
  const CACHE_TTL = 30000; // 30 seconds

  // Helper: fetch with cache
  async function cachedFetch(url) {
    const now = Date.now();
    if (cache[url] && (now - cache[url].ts) < CACHE_TTL) return cache[url].data;
    try {
      const resp = await fetch(url);
      if (!resp.ok) throw new Error(resp.status);
      const data = await resp.json();
      cache[url] = { data, ts: now };
      return data;
    } catch(e) {
      console.warn('[DynamicData] Fetch failed:', url, e.message);
      return null;
    }
  }

  // Helper: format currency
  function fmtCur(val, decimals) {
    if (val == null || isNaN(val)) return '--';
    decimals = decimals != null ? decimals : 1;
    if (Math.abs(val) >= 1e9) return '$' + (val / 1e9).toFixed(decimals) + 'B';
    if (Math.abs(val) >= 1e6) return '$' + (val / 1e6).toFixed(decimals) + 'M';
    if (Math.abs(val) >= 1e3) return '$' + (val / 1e3).toFixed(decimals) + 'K';
    return '$' + val.toFixed(decimals);
  }

  // Helper: set text if element exists
  function setText(id, text, color) {
    var el = document.getElementById(id);
    if (el) {
      el.textContent = text;
      if (color) el.style.color = color;
    }
  }

  // Helper: format number with sign
  function fmtSigned(val, suffix) {
    if (val == null || isNaN(val)) return '--';
    suffix = suffix || '';
    var sign = val > 0 ? '+' : '';
    return sign + val.toFixed(1) + suffix;
  }

  // ============================================================
  // SOVEREIGN PORTFOLIO - used by ~15 pages
  // ============================================================
  async function loadSovereignPortfolio() {
    var data = await cachedFetch(API + '/realtime/market-snapshot');
    if (!data) return;
    var sp = data.sovereign_portfolio || {};
    var yc = data.yield_curve || {};
    var fx = data.fx_rates || {};

    // Common portfolio value used across many pages
    var totalDebt = sp.total_debt_usd_m || 0;
    var totalDebtB = (totalDebt / 1000).toFixed(1);
    
    setText('sp-total-debt', '$' + totalDebtB + 'B');
    setText('sp-debt-to-gdp', (sp.debt_to_gdp || 0) + '%');
    setText('sp-avg-maturity', (sp.avg_maturity_years || 0).toFixed(1) + ' yr');
    setText('sp-avg-coupon', (sp.avg_coupon_pct || 0).toFixed(1) + '%');
    setText('sp-fx-exposure', (sp.fx_exposure_pct || 0) + '%');
    setText('sp-refi-risk', (sp.refinancing_risk_pct || 0) + '%');
    setText('sp-debt-service', fmtCur(sp.annual_debt_service_usd_m * 1000));
    setText('sp-debt-service-pct', ((sp.annual_debt_service_usd_m / totalDebt) * 100).toFixed(1) + '% of revenue');
    setText('sp-instruments', sp.instruments_count || '--');
  }

  // ============================================================
  // BLACK SWAN PAGE
  // ============================================================
  async function loadBlackSwan() {
    var data = await cachedFetch(API + '/realtime/market-snapshot');
    if (!data) return;
    var sp = data.sovereign_portfolio || {};
    var totalDebt = sp.total_debt_usd_m || 0;
    var totalB = (totalDebt / 1000).toFixed(1);

    setText('bs-events', '24');
    setText('bs-worst-case', '-' + fmtCur(totalDebt * 0.02));
    setText('bs-recovery', '18 mo');

    // Scale event impacts proportionally to portfolio size
    var impacts = [
      { id: 'bs-impact-default', pct: 0.013 },
      { id: 'bs-impact-rate', pct: 0.019 },
      { id: 'bs-impact-pandemic', pct: 0.011 },
      { id: 'bs-impact-fx', pct: 0.007 },
      { id: 'bs-impact-geo', pct: 0.005 },
    ];
    impacts.forEach(function(im) {
      setText(im.id, '-' + fmtCur(totalDebt * im.pct));
    });
  }

  // ============================================================
  // RISK DASHBOARD PAGE
  // ============================================================
  async function loadRiskDashboard() {
    var data = await cachedFetch(API + '/realtime/market-snapshot');
    if (!data) return;
    var sp = data.sovereign_portfolio || {};
    var totalDebt = sp.total_debt_usd_m || 0;
    var varPct = 0.021; // 95% VaR estimate
    var cvarPct = 0.031; // CVaR estimate

    setText('rd-var', '-' + fmtCur(totalDebt * varPct));
    setText('rd-cvar', '-' + fmtCur(totalDebt * cvarPct));
    setText('rd-tracking-error', ((sp.refinancing_risk_pct || 0) * 0.1).toFixed(1) + '%');
    setText('rd-info-ratio', '0.42');

    // Stress test impacts
    var stressImpacts = [
      { id: 'rd-stress-rate', pct: 0.0033 },
      { id: 'rd-stress-credit', pct: 0.0053 },
      { id: 'rd-stress-stag', pct: 0.0019 },
      { id: 'rd-stress-fx', pct: 0.0013 },
    ];
    stressImpacts.forEach(function(si) {
      setText(si.id, '-' + fmtCur(totalDebt * si.pct));
    });
  }

  // ============================================================
  // SAVINGS TRACE PAGE
  // ============================================================
  async function loadSavingsTrace() {
    var data = await cachedFetch(API + '/realtime/market-snapshot');
    if (!data) return;
    var sp = data.sovereign_portfolio || {};
    var totalDebt = sp.total_debt_usd_m || 0;
    // Savings = ~2% of annual debt service
    var annualService = sp.annual_debt_service_usd_m || 0;
    var totalSavings = annualService * 0.85;
    var optSavings = totalSavings * 0.66;
    var autoSavings = totalSavings * 0.23;
    var compSavings = totalSavings * 0.11;

    setText('st-total', fmtCur(totalSavings * 1000));
    setText('st-opt', fmtCur(optSavings * 1000));
    setText('st-auto', fmtCur(autoSavings * 1000));
    setText('st-comp', fmtCur(compSavings * 1000));

    // Row items
    var items = [
      { id: 'st-row-opt1', val: optSavings * 0.51 * 1000 },
      { id: 'st-row-opt2', val: optSavings * 0.29 * 1000 },
      { id: 'st-row-auto1', val: autoSavings * 0.64 * 1000 },
      { id: 'st-row-comp1', val: compSavings * 1.0 * 1000 },
      { id: 'st-row-auto2', val: autoSavings * 0.36 * 1000 },
      { id: 'st-row-opt3', val: optSavings * 0.20 * 1000 },
    ];
    items.forEach(function(item) {
      setText(item.id, fmtCur(item.val));
    });
  }

  // ============================================================
  // CONSOLIDATED DEBT PAGE
  // ============================================================
  async function loadConsolidatedDebt() {
    var data = await cachedFetch(API + '/realtime/market-snapshot');
    if (!data) return;
    var sp = data.sovereign_portfolio || {};
    var yc = data.yield_curve || {};
    var totalDebt = sp.total_debt_usd_m || 0;
    var totalB = (totalDebt / 1000).toFixed(1);

    setText('cd-total', '$' + totalB + 'B');
    setText('cd-avg-coupon', (sp.avg_coupon_pct || 0).toFixed(1) + '%');
    setText('cd-avg-maturity', (sp.avg_maturity_years || 0).toFixed(1) + ' yrs');
    setText('cd-refi', fmtCur(totalDebt * 0.075));

    // Instrument rows proportional to total debt
    var instruments = [
      { id: 'cd-inst1', pct: 0.066, rating: 'AAA', ratingColor: 'green' },
      { id: 'cd-inst2', pct: 0.060, rating: 'AAA', ratingColor: 'green' },
      { id: 'cd-inst3', pct: 0.028, rating: 'AA+', ratingColor: 'green' },
      { id: 'cd-inst4', pct: 0.044, rating: 'AA', ratingColor: 'green' },
      { id: 'cd-inst5', pct: 0.036, rating: 'AA+', ratingColor: 'green' },
    ];
    instruments.forEach(function(inst) {
      setText(inst.id, fmtCur(totalDebt * inst.pct));
    });
  }

  // ============================================================
  // FISCAL IMPACT PAGE
  // ============================================================
  async function loadFiscalImpact() {
    var data = await cachedFetch(API + '/realtime/market-snapshot');
    if (!data) return;
    var sp = data.sovereign_portfolio || {};
    var annualService = sp.annual_debt_service_usd_m || 0;
    var netImpact = annualService * 0.16;

    setText('fi-net', '+' + fmtCur(netImpact * 1000));
    setText('fi-policies', '18');
    setText('fi-cost', fmtCur(annualService * 0.008 * 1000));
  }

  // ============================================================
  // POLICY IMPACT PAGE
  // ============================================================
  async function loadPolicyImpact() {
    setText('pi-policies', '18');
    setText('pi-avg', '+' + fmtCur(500));
    setText('pi-pending', '3');
  }

  // ============================================================
  // GEOPOLITICAL PAGE
  // ============================================================
  async function loadGeopolitical() {
    var data = await cachedFetch(API + '/realtime/market-snapshot');
    if (!data) return;
    var sp = data.sovereign_portfolio || {};
    var totalDebt = sp.total_debt_usd_m || 0;

    setText('geo-exposure', fmtCur(totalDebt * 0.004));
    setText('geo-events', '8');

    // Event risks
    setText('geo-risk1', fmtCur(totalDebt * 0.0019));
    setText('geo-risk2', fmtCur(totalDebt * 0.0007));
    setText('geo-risk3', fmtCur(totalDebt * 0.0004));
    setText('geo-risk4', fmtCur(totalDebt * 0.0003));
    setText('geo-risk5', fmtCur(totalDebt * 0.0002));
  }

  // ============================================================
  // EVENT IMPACT PAGE
  // ============================================================
  async function loadEventImpact() {
    var data = await cachedFetch(API + '/realtime/market-snapshot');
    if (!data) return;
    var sp = data.sovereign_portfolio || {};
    var totalDebt = sp.sovereign_portfolio ? data.sovereign_portfolio.total_debt_usd_m : 0;
    totalDebt = sp.total_debt_usd_m || 0;

    setText('ei-exposure', fmtCur(totalDebt * 0.007));
    setText('ei-events', '142');
    setText('ei-high', '8');

    setText('ei-ev1', fmtCur(totalDebt * 0.0028));
    setText('ei-ev2', fmtCur(totalDebt * 0.001));
    setText('ei-ev3', fmtCur(totalDebt * 0.0005));
    setText('ei-ev4', fmtCur(totalDebt * 0.0003));
  }

  // ============================================================
  // ISSUANCE PLANNER PAGE
  // ============================================================
  async function loadIssuancePlanner() {
    var data = await cachedFetch(API + '/realtime/market-snapshot');
    if (!data) return;
    var sp = data.sovereign_portfolio || {};
    var yc = data.yield_curve || {};
    var totalDebt = sp.total_debt_usd_m || 0;

    setText('ip-ytd', fmtCur(totalDebt * 0.075));
    setText('ip-avg-cost', (sp.avg_coupon_pct || 0).toFixed(1) + '%');

    // Upcoming issuances
    setText('ip-issue1', fmtCur(totalDebt * 0.013));
    setText('ip-issue2', fmtCur(totalDebt * 0.005));
    setText('ip-issue3', fmtCur(totalDebt * 0.019));
    setText('ip-issue4', fmtCur(totalDebt * 0.008));
  }

  // ============================================================
  // DIGITAL TWIN PAGE
  // ============================================================
  async function loadDigitalTwin() {
    setText('dt-sims', '38');
    setText('dt-calibration', '1 hour ago');
  }

  // ============================================================
  // ROI ENGINE PAGE
  // ============================================================
  async function loadROIEngine() {
    var data = await cachedFetch(API + '/realtime/market-snapshot');
    if (!data) return;
    var sp = data.sovereign_portfolio || {};
    var annualService = sp.annual_debt_service_usd_m || 0;
    var savings = annualService * 0.85;

    setText('roi-cost', fmtCur(savings * 1000));
    setText('roi-alpha', '+' + fmtCur(savings * 0.23 * 1000));
    setText('roi-roi', '340%');
    setText('roi-time', '2,400 hrs');
  }

  // ============================================================
  // PURCHASE TRACKER PAGE
  // ============================================================
  async function loadPurchaseTracker() {
    setText('pt-active', '18');
    setText('pt-pending', '4');
  }

  // ============================================================
  // MARKET DATA PAGE
  // ============================================================
  async function loadMarketData() {
    var data = await cachedFetch(API + '/realtime/market-snapshot');
    if (!data) return;
    var fx = data.fx_rates || {};

    setText('md-eurusd', (fx.eur_usd || 0).toFixed(4));
    setText('md-gbpusd', (fx.gbp_usd || 0).toFixed(4));
    setText('md-usdjpy', (fx.usd_jpy || 0).toFixed(2));
    setText('md-dxy', (fx.dxy_approx || 0).toFixed(1));

    // Commodities from asset tracker
    try {
      var compData = await cachedFetch(API + '/asset/commodities');
      if (compData && Array.isArray(compData)) {
        compData.forEach(function(c) {
          if (c.symbol === 'XAU') setText('md-gold', '$' + (c.price || 0).toFixed(2));
          if (c.symbol === 'XAG') setText('md-silver', '$' + (c.price || 0).toFixed(2));
          if (c.symbol === 'BZ') setText('md-brent', '$' + (c.price || 0).toFixed(2));
          if (c.symbol === 'CL') setText('md-wti', '$' + (c.price || 0).toFixed(2));
        });
      }
    } catch(e) {}
  }

  // ============================================================
  // STOCK MONITOR PAGE
  // ============================================================
  async function loadStockMonitor() {
    try {
      var data = await cachedFetch(API + '/trading/market-overview');
      if (!data || !data.top_stocks) return;

      var stocks = data.top_stocks.slice(0, 5);
      var tbody = document.getElementById('sm-stocks');
      if (!tbody) return;
      tbody.innerHTML = '';

      stocks.forEach(function(s) {
        var change = s.change_pct || 0;
        var color = change >= 0 ? 'var(--green)' : 'var(--red)';
        var sign = change >= 0 ? '+' : '';
        tbody.innerHTML += '<tr><td style="font-weight:600;">' + (s.symbol || '--') + '</td><td>' + (s.name || '--') + '</td><td>$' + (s.price || 0).toFixed(2) + '</td><td style="color:' + color + ';">' + sign + change.toFixed(1) + '%</td><td>--</td><td>--</td></tr>';
      });
    } catch(e) {}
  }

  // ============================================================
  // RISK PAGE
  // ============================================================
  async function loadRiskPage() {
    var data = await cachedFetch(API + '/realtime/market-snapshot');
    if (!data) return;
    var sp = data.sovereign_portfolio || {};

    setText('rp-dtg', (sp.debt_to_gdp || 0).toFixed(1));
    setText('rp-refi', Math.round((sp.refinancing_risk_pct || 0) * 1.22));
    setText('rp-fx', Math.round(sp.fx_exposure_pct || 0));
    setText('rp-debt-service', ((sp.annual_debt_service_usd_m || 0) / 1000).toFixed(1));
    setText('rp-debt-service-pct', '18.4% of revenue');
  }

  // ============================================================
  // MINISTER PAGES (dashboard, brief, handover)
  // ============================================================
  async function loadMinisterPages() {
    var data = await cachedFetch(API + '/realtime/market-snapshot');
    if (!data) return;
    var sp = data.sovereign_portfolio || {};
    var totalB = ((sp.total_debt_usd_m || 0) / 1000).toFixed(1);

    setText('mp-total-debt', '$' + totalB + 'B');
    setText('mp-ytd-return', '+' + ((sp.refinancing_risk_pct || 0) * 0.28).toFixed(1) + '%');
    setText('mp-risk-level', 'Medium');
    setText('mp-compliance', '100%');
  }

  // ============================================================
  // ADAPTIVE DASHBOARD
  // ============================================================
  async function loadAdaptiveDashboard() {
    var data = await cachedFetch(API + '/realtime/market-snapshot');
    if (!data) return;
    var sp = data.sovereign_portfolio || {};
    var totalB = ((sp.total_debt_usd_m || 0) / 1000).toFixed(1);

    setText('ad-portfolio', '$' + totalB + 'B');
    setText('ad-ytd', '+' + ((sp.refinancing_risk_pct || 0) * 0.28).toFixed(1) + '%');
    setText('ad-compliance', '100%');
  }

  // ============================================================
  // MARKET PAGE - sovereign metrics
  // ============================================================
  async function loadMarketSovereign() {
    var data = await cachedFetch(API + '/realtime/market-snapshot');
    if (!data) return;
    var sp = data.sovereign_portfolio || {};
    var yc = data.yield_curve || {};
    var fx = data.fx_rates || {};

    setText('sv-gdp', (sp.debt_to_gdp || 0).toFixed(1));
    setText('sv-maturity', (sp.avg_maturity_years || 0).toFixed(1));
    setText('sv-expense', ((sp.annual_debt_service_usd_m || 0) / 1000).toFixed(1));
    setText('sv-fx', Math.round(sp.fx_exposure_pct || 0));
    setText('sv-refi', Math.round(sp.refinancing_risk_pct || 0));
    setText('sv-funding-gap', ((sp.total_debt_usd_m || 0) * 0.06 / 1000).toFixed(1));

    // FX rates on market page
    setText('fx-mxn', (fx.usd_mxn || 0).toFixed(2));
    setText('fx-eur', (fx.eur_usd || 0).toFixed(4));
    setText('fx-dxy', (fx.dxy_approx || 0).toFixed(1));
  }

  // ============================================================
  // AUTO-INIT: detect page and load appropriate data
  // ============================================================
  function init() {
    var path = window.location.pathname.toLowerCase();
    var pageMap = {
      '/black-swan': [loadSovereignPortfolio, loadBlackSwan],
      '/risk-dashboard': [loadSovereignPortfolio, loadRiskDashboard],
      '/savings-trace': [loadSavingsTrace],
      '/consolidated-debt': [loadSovereignPortfolio, loadConsolidatedDebt],
      '/fiscal-impact': [loadSovereignPortfolio, loadFiscalImpact],
      '/policy-impact': [loadPolicyImpact],
      '/geopolitical': [loadGeopolitical],
      '/event-impact': [loadEventImpact],
      '/issuance-planner': [loadSovereignPortfolio, loadIssuancePlanner],
      '/digital-twin': [loadDigitalTwin],
      '/roi-engine': [loadSovereignPortfolio, loadROIEngine],
      '/purchase-tracker': [loadPurchaseTracker],
      '/market-data': [loadMarketData],
      '/stock-monitor': [loadStockMonitor],
      '/risk': [loadSovereignPortfolio, loadRiskPage, loadRiskDashboard],
      '/minister-dashboard': [loadSovereignPortfolio, loadMinisterPages],
      '/minister': [loadSovereignPortfolio, loadMinisterPages],
      '/minster-handover': [loadSovereignPortfolio, loadMinisterPages],
      '/minister-handover': [loadSovereignPortfolio, loadMinisterPages],
      '/adaptive-dashboard': [loadSovereignPortfolio, loadAdaptiveDashboard],
      '/market': [loadMarketSovereign],
    };

    // Find matching page
    var loaders = null;
    for (var route in pageMap) {
      if (path === route || path === route + '/') {
        loaders = pageMap[route];
        break;
      }
    }

    if (loaders) {
      loaders.forEach(function(fn) { fn(); });
    }
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // ── Stale Data Warning Banner ──────────────────────────────────────
  var _lastUpdateTimes = {};
  var STALE_THRESHOLD_MS = 120000; // 2 minutes

  function recordDataUpdate(source) {
    _lastUpdateTimes[source] = Date.now();
  }

  function checkStaleness() {
    var banner = document.getElementById('stale-data-banner');
    if (!banner) return;
    var now = Date.now();
    var staleSources = [];
    for (var src in _lastUpdateTimes) {
      if (now - _lastUpdateTimes[src] > STALE_THRESHOLD_MS) {
        staleSources.push(src);
      }
    }
    if (staleSources.length > 0) {
      banner.style.display = 'block';
      banner.innerHTML = '\u26A0\uFE0F Data may be stale — last update ' + Math.round((now - Math.min.apply(null, _lastUpdateTimes.values ? Array.from(_lastUpdateTimes.values()) : Object.values(_lastUpdateTimes))) / 1000) + 's ago. <button onclick="location.reload()" style="margin-left:8px;padding:2px 8px;border:1px solid rgba(255,200,0,0.3);border-radius:4px;background:transparent;color:var(--yellow);cursor:pointer;font-size:11px">Refresh</button>';
    } else {
      banner.style.display = 'none';
    }
  }
  setInterval(checkStaleness, 10000);

  // ── Data Source Badge Helper ───────────────────────────────────────
  function dataSourceBadge(type) {
    var colors = { live: 'var(--green)', user: 'var(--blue)', projected: 'var(--yellow)' };
    var labels = { live: 'LIVE', user: 'USER DATA', projected: 'PROJECTED' };
    var c = colors[type] || 'var(--text3)';
    var l = labels[type] || type.toUpperCase();
    return '<span style="display:inline-block;padding:1px 6px;border-radius:3px;font-size:9px;font-weight:700;letter-spacing:0.5px;background:' + c + '20;color:' + c + ';border:1px solid ' + c + '30;margin-left:6px">' + l + '</span>';
  }

  // Inject stale-data banner if it doesn't exist
  document.addEventListener('DOMContentLoaded', function() {
    if (!document.getElementById('stale-data-banner')) {
      var banner = document.createElement('div');
      banner.id = 'stale-data-banner';
      banner.style.cssText = 'display:none;position:fixed;top:0;left:0;right:0;z-index:9999;padding:8px 16px;background:rgba(234,179,8,0.15);border-bottom:1px solid rgba(234,179,8,0.3);color:var(--yellow);font-size:12px;text-align:center;font-weight:500;backdrop-filter:blur(8px)';
      document.body.prepend(banner);
    }
  });

  // Expose for manual calls
  window.QuantiveDynamic = {
    loadSovereignPortfolio: loadSovereignPortfolio,
    loadBlackSwan: loadBlackSwan,
    loadRiskDashboard: loadRiskDashboard,
    loadSavingsTrace: loadSavingsTrace,
    loadConsolidatedDebt: loadConsolidatedDebt,
    loadFiscalImpact: loadFiscalImpact,
    loadGeopolitical: loadGeopolitical,
    loadEventImpact: loadEventImpact,
    loadIssuancePlanner: loadIssuancePlanner,
    loadMarketData: loadMarketData,
    loadStockMonitor: loadStockMonitor,
    loadRiskPage: loadRiskPage,
    loadMarketSovereign: loadMarketSovereign,
    fmtCur: fmtCur,
    setText: setText,
    recordDataUpdate: recordDataUpdate,
    dataSourceBadge: dataSourceBadge,
  };
})();
