import { useCallback, useState } from 'react';
import { Calculator, TrendingUp, DollarSign, BarChart3, CheckCircle, ArrowRight } from 'lucide-react';
import { api } from '../api';

interface PortfolioInput {
  total_debt_outstanding: number;
  annual_issuance: number;
  currency: string;
  debt_to_gdp: number;
}

interface QuoteResult {
  quote: {
    model: string;
    term: string;
    base_fee_annual: number;
    outcome_fee_annual: number;
    total_fee_annual: number;
    total_fee_term: number;
    roi_ratio: number;
    cost_per_basis_point: number;
    legacy_cost_comparison: number;
    competitor_comparison: number;
  };
  savings_estimate: {
    financing_cost_savings_bps: number;
    refinancing_savings_usd: number;
    risk_reduction_bps: number;
    total_annual_savings_usd: number;
    confidence_level: number;
  };
}

const TERM_OPTIONS = [
  { value: 'annual', label: 'Annual', years: 1 },
  { value: 'multi_year_3', label: '3-Year', years: 3, discount: '10% discount' },
  { value: 'multi_year_5', label: '5-Year', years: 5, discount: '18% discount' },
  { value: 'multi_year_10', label: '10-Year', years: 10, discount: '30% discount' },
];

function formatCurrency(value: number): string {
  if (value >= 1e12) return `$${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

function formatBps(bps: number): string {
  return `${bps.toFixed(1)} bps`;
}

export default function OutcomePricingPage() {
  const [portfolio, setPortfolio] = useState<PortfolioInput>({
    total_debt_outstanding: 50000000000, // $50B default
    annual_issuance: 5000000000, // $5B default
    currency: 'USD',
    debt_to_gdp: 45,
  });
  const [selectedTerm, setSelectedTerm] = useState('multi_year_5');
  const [quote, setQuote] = useState<QuoteResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const calculateQuote = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.pricing.customize({
        debt_outstanding_usd: portfolio.total_debt_outstanding,
        currency: portfolio.currency,
        optimization_type: 'basis_points',
        term: selectedTerm,
        portfolio,
      });
      setQuote({
        quote: {
          model: 'basis_points',
          term: selectedTerm,
          base_fee_annual: result.base_price,
          outcome_fee_annual: result.discount,
          total_fee_annual: result.final_price,
          total_fee_term: result.final_price,
          roi_ratio: result.debt_outstanding > 0 ? result.final_price / result.debt_outstanding : 0,
          cost_per_basis_point: result.base_price,
          legacy_cost_comparison: result.base_price * 2,
          competitor_comparison: result.base_price * 1.5,
        },
        savings_estimate: {
          financing_cost_savings_bps: 10,
          refinancing_savings_usd: result.debt_outstanding * 0.001,
          risk_reduction_bps: 5,
          total_annual_savings_usd: result.debt_outstanding * 0.002,
          confidence_level: 0.85,
        },
      } as QuoteResult);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to calculate quote');
    } finally {
      setLoading(false);
    }
  }, [portfolio, selectedTerm]);

  const roiReport = quote ? {
    annual_investment: quote.quote.total_fee_annual,
    annual_savings: quote.savings_estimate.total_annual_savings_usd,
    net_benefit: quote.savings_estimate.total_annual_savings_usd - quote.quote.total_fee_annual,
    roi_ratio: quote.quote.roi_ratio,
    payback_months: Math.round(
      (quote.quote.total_fee_annual / (quote.savings_estimate.total_annual_savings_usd / 12)) * 10
    ) / 10,
  } : null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
            <Calculator className="w-8 h-8 text-blue-600" />
            Outcome-Based Pricing
          </h1>
          <p className="text-slate-600 mt-2">
            Pay based on the value we deliver. No seats, no subscriptions — just results.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Input Panel */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Your Portfolio</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Total Debt Outstanding
                  </label>
                  <div className="relative">
                    <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                      type="number"
                      value={portfolio.total_debt_outstanding}
                      onChange={(e) =>
                        setPortfolio({ ...portfolio, total_debt_outstanding: Number(e.target.value) })
                      }
                      className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="50000000000"
                    />
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    {formatCurrency(portfolio.total_debt_outstanding)}
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Annual Issuance
                  </label>
                  <div className="relative">
                    <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                      type="number"
                      value={portfolio.annual_issuance}
                      onChange={(e) =>
                        setPortfolio({ ...portfolio, annual_issuance: Number(e.target.value) })
                      }
                      className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="5000000000"
                    />
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    {formatCurrency(portfolio.annual_issuance)}
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Debt-to-GDP Ratio
                  </label>
                  <input
                    type="number"
                    value={portfolio.debt_to_gdp}
                    onChange={(e) =>
                      setPortfolio({ ...portfolio, debt_to_gdp: Number(e.target.value) })
                    }
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="45"
                  />
                  <p className="text-xs text-slate-500 mt-1">{portfolio.debt_to_gdp}%</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Contract Term
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {TERM_OPTIONS.map((term) => (
                      <button
                        key={term.value}
                        onClick={() => setSelectedTerm(term.value)}
                        className={`p-3 rounded-lg border-2 text-left ${
                          selectedTerm === term.value
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-slate-200 hover:border-slate-300'
                        }`}
                      >
                        <div className="font-medium text-slate-900">{term.label}</div>
                        {term.discount && (
                          <div className="text-xs text-emerald-600">{term.discount}</div>
                        )}
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  onClick={calculateQuote}
                  disabled={loading}
                  className="w-full py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
                >
                  {loading ? 'Calculating...' : 'Calculate Pricing'}
                </button>
              </div>
            </div>

            {/* How It Works */}
            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200 mt-6">
              <h3 className="font-semibold text-slate-900 mb-3">How It Works</h3>
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-blue-600 text-sm font-bold">1</span>
                  </div>
                  <div>
                    <div className="font-medium text-slate-900">Base Fee</div>
                    <div className="text-sm text-slate-600">Fixed annual fee based on portfolio size</div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-blue-600 text-sm font-bold">2</span>
                  </div>
                  <div>
                    <div className="font-medium text-slate-900">Outcome Fee</div>
                    <div className="text-sm text-slate-600">Small % of savings we deliver</div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-blue-600 text-sm font-bold">3</span>
                  </div>
                  <div>
                    <div className="font-medium text-slate-900">You Win</div>
                    <div className="text-sm text-slate-600">Net savings after our fee</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Results Panel */}
          <div className="lg:col-span-2">
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                <p className="text-red-600">{error}</p>
              </div>
            )}

            {!quote && !loading && (
              <div className="bg-white rounded-xl shadow-sm p-12 border border-slate-200 text-center">
                <Calculator className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-slate-900 mb-2">Enter Your Portfolio Details</h3>
                <p className="text-slate-600">
                  Configure your debt portfolio and contract term to see your custom pricing.
                </p>
              </div>
            )}

            {quote && (
              <div className="space-y-6">
                {/* ROI Summary */}
                {roiReport && (
                  <div className="bg-gradient-to-r from-emerald-500 to-blue-600 rounded-xl shadow-lg p-6 text-white">
                    <h2 className="text-lg font-semibold mb-4">Your Investment Return</h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <div className="text-emerald-100 text-sm">Annual Investment</div>
                        <div className="text-2xl font-bold">{formatCurrency(roiReport.annual_investment)}</div>
                      </div>
                      <div>
                        <div className="text-emerald-100 text-sm">Annual Savings</div>
                        <div className="text-2xl font-bold">{formatCurrency(roiReport.annual_savings)}</div>
                      </div>
                      <div>
                        <div className="text-emerald-100 text-sm">Net Benefit</div>
                        <div className="text-2xl font-bold text-emerald-200">
                          {formatCurrency(roiReport.net_benefit)}
                        </div>
                      </div>
                      <div>
                        <div className="text-emerald-100 text-sm">ROI</div>
                        <div className="text-2xl font-bold">{roiReport.roi_ratio}x</div>
                      </div>
                    </div>
                    <div className="mt-4 pt-4 border-t border-white/20">
                      <div className="text-sm text-emerald-100">
                        Payback period: <span className="font-bold text-white">{roiReport.payback_months} months</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Pricing Breakdown */}
                <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
                  <h2 className="text-lg font-semibold text-slate-900 mb-4">Pricing Breakdown</h2>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-4 bg-slate-50 rounded-lg">
                      <div className="text-sm text-slate-500">Base Fee (Annual)</div>
                      <div className="text-xl font-bold text-slate-900">
                        {formatCurrency(quote.quote.base_fee_annual)}
                      </div>
                    </div>
                    <div className="p-4 bg-slate-50 rounded-lg">
                      <div className="text-sm text-slate-500">Outcome Fee (Annual)</div>
                      <div className="text-xl font-bold text-blue-600">
                        {formatCurrency(quote.quote.outcome_fee_annual)}
                      </div>
                    </div>
                    <div className="p-4 bg-blue-50 rounded-lg">
                      <div className="text-sm text-blue-600">Total Fee (Annual)</div>
                      <div className="text-xl font-bold text-blue-700">
                        {formatCurrency(quote.quote.total_fee_annual)}
                      </div>
                    </div>
                  </div>
                  {quote.quote.term !== 'annual' && (
                    <div className="mt-4 p-4 bg-emerald-50 rounded-lg">
                      <div className="text-sm text-emerald-600">Total Over Contract Term</div>
                      <div className="text-xl font-bold text-emerald-700">
                        {formatCurrency(quote.quote.total_fee_term)}
                      </div>
                    </div>
                  )}
                </div>

                {/* Savings Breakdown */}
                <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
                  <h2 className="text-lg font-semibold text-slate-900 mb-4">Estimated Savings</h2>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                      <div>
                        <div className="font-medium text-slate-900">Financing Cost Reduction</div>
                        <div className="text-sm text-slate-600">Lower interest rates through optimization</div>
                      </div>
                      <div className="text-right">
                        <div className="font-bold text-emerald-600">
                          {formatBps(quote.savings_estimate.financing_cost_savings_bps)}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                      <div>
                        <div className="font-medium text-slate-900">Refinancing Optimization</div>
                        <div className="text-sm text-slate-600">Better timing and structure</div>
                      </div>
                      <div className="text-right">
                        <div className="font-bold text-emerald-600">
                          {formatCurrency(quote.savings_estimate.refinancing_savings_usd)}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                      <div>
                        <div className="font-medium text-slate-900">Risk Reduction</div>
                        <div className="text-sm text-slate-600">Lower risk = lower cost of capital</div>
                      </div>
                      <div className="text-right">
                        <div className="font-bold text-emerald-600">
                          {formatBps(quote.savings_estimate.risk_reduction_bps)}
                        </div>
                      </div>
                    </div>
                    <div className="p-4 bg-emerald-50 rounded-lg">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold text-emerald-900">Total Annual Savings</div>
                        <div className="text-2xl font-bold text-emerald-700">
                          {formatCurrency(quote.savings_estimate.total_annual_savings_usd)}
                        </div>
                      </div>
                      <div className="text-sm text-emerald-600 mt-1">
                        Confidence: {(quote.savings_estimate.confidence_level * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>
                </div>

                {/* Comparison */}
                <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
                  <h2 className="text-lg font-semibold text-slate-900 mb-4">Cost Comparison</h2>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border-2 border-blue-200">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                          <span className="text-white font-bold">Q</span>
                        </div>
                        <div>
                          <div className="font-medium text-slate-900">Quantive (Outcome-Based)</div>
                          <div className="text-sm text-slate-600">Pay only for results</div>
                        </div>
                      </div>
                      <div className="text-xl font-bold text-blue-700">
                        {formatCurrency(quote.quote.total_fee_annual)}/yr
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-slate-600 rounded-lg flex items-center justify-center">
                          <span className="text-white font-bold">B</span>
                        </div>
                        <div>
                          <div className="font-medium text-slate-900">Bloomberg Terminal</div>
                          <div className="text-sm text-slate-600">50 users × $24K/year</div>
                        </div>
                      </div>
                      <div className="text-xl font-bold text-slate-600">
                        {formatCurrency(quote.quote.legacy_cost_comparison)}/yr
                      </div>
                    </div>
                    <div className="p-3 bg-emerald-50 rounded-lg">
                      <div className="flex items-center gap-2">
                        <CheckCircle className="w-5 h-5 text-emerald-600" />
                        <span className="font-medium text-emerald-900">
                          Save {formatCurrency(quote.quote.legacy_cost_comparison - quote.quote.total_fee_annual)}/yr vs Bloomberg
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* CTA */}
                <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl shadow-lg p-6 text-white">
                  <h2 className="text-xl font-semibold mb-2">Ready to Start Saving?</h2>
                  <p className="text-blue-100 mb-4">
                    Launch a 12-month free pilot and see the results for yourself.
                  </p>
                  <div className="flex gap-3">
                    <button className="px-6 py-3 bg-white text-blue-700 rounded-lg font-medium hover:bg-blue-50 flex items-center gap-2">
                      Start Free Pilot
                      <ArrowRight className="w-4 h-4" />
                    </button>
                    <button className="px-6 py-3 bg-blue-600 text-white border border-blue-500 rounded-lg font-medium hover:bg-blue-800">
                      Schedule Demo
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
