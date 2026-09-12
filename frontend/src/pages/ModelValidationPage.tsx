import { useCallback, useState } from 'react';
import {
  Cpu, Play, CheckCircle, AlertTriangle, Clock,
  TrendingUp, BarChart3, Activity, RefreshCw
} from 'lucide-react';
import { api } from '../api';
import type { ValidationResult } from '../types';

export default function ModelValidationPage() {
  const [solutionId, setSolutionId] = useState('');
  const [validations, setValidations] = useState<ValidationResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [backtestResult, setBacktestResult] = useState<any>(null);

  const runValidation = async (type: string) => {
    if (!solutionId) return;
    setLoading(true);
    try {
      let result;
      switch (type) {
        case 'feasibility':
          result = await api.modelValidation.validate({ strategy_id: solutionId, portfolio_data: {} });
          break;
        case 'optimality':
          result = await api.modelValidation.validateOptimality(solutionId);
          break;
        case 'stability':
          result = await api.modelValidation.validateStability(solutionId);
          break;
        default:
          result = await api.modelValidation.validate({ strategy_id: solutionId, portfolio_data: {} });
      }
      setValidations(prev => [result, ...prev]);
    } catch (e) {
      console.error('Validation failed:', e);
    } finally {
      setLoading(false);
    }
  };

  const runBacktest = async () => {
    if (!solutionId) return;
    setLoading(true);
    try {
      const result = await api.modelValidation.backtest(solutionId);
      setBacktestResult(result);
    } catch (e) {
      console.error('Backtest failed:', e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
            <Cpu className="w-8 h-8 text-blue-600" />
            AI Model Validation & Backtesting
          </h1>
          <p className="text-slate-600 mt-2">
            Validate debt optimization models for feasibility, optimality, and stability.
          </p>
        </div>

        {/* Input */}
        <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200 mb-6">
          <div className="flex items-end gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-slate-700 mb-1">Solution ID</label>
              <input
                type="text"
                value={solutionId}
                onChange={(e) => setSolutionId(e.target.value)}
                placeholder="Enter solution ID to validate..."
                className="w-full border border-slate-300 rounded-lg px-3 py-2"
              />
            </div>
          </div>
        </div>

        {/* Validation Actions */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <button
            onClick={() => runValidation('feasibility')}
            disabled={!solutionId || loading}
            className="bg-white rounded-xl shadow-sm p-6 border border-slate-200 hover:shadow-md transition-shadow text-left disabled:opacity-50"
          >
            <Activity className="w-8 h-8 text-blue-600 mb-3" />
            <h3 className="font-semibold text-slate-900">Feasibility</h3>
            <p className="text-sm text-slate-500 mt-1">Check constraints & bounds</p>
          </button>
          <button
            onClick={() => runValidation('optimality')}
            disabled={!solutionId || loading}
            className="bg-white rounded-xl shadow-sm p-6 border border-slate-200 hover:shadow-md transition-shadow text-left disabled:opacity-50"
          >
            <TrendingUp className="w-8 h-8 text-emerald-600 mb-3" />
            <h3 className="font-semibold text-slate-900">Optimality</h3>
            <p className="text-sm text-slate-500 mt-1">Gap analysis vs bounds</p>
          </button>
          <button
            onClick={() => runValidation('stability')}
            disabled={!solutionId || loading}
            className="bg-white rounded-xl shadow-sm p-6 border border-slate-200 hover:shadow-md transition-shadow text-left disabled:opacity-50"
          >
            <BarChart3 className="w-8 h-8 text-amber-600 mb-3" />
            <h3 className="font-semibold text-slate-900">Stability</h3>
            <p className="text-sm text-slate-500 mt-1">Solution robustness test</p>
          </button>
          <button
            onClick={runBacktest}
            disabled={!solutionId || loading}
            className="bg-white rounded-xl shadow-sm p-6 border border-slate-200 hover:shadow-md transition-shadow text-left disabled:opacity-50"
          >
            <Play className="w-8 h-8 text-purple-600 mb-3" />
            <h3 className="font-semibold text-slate-900">Backtest</h3>
            <p className="text-sm text-slate-500 mt-1">Historical performance</p>
          </button>
        </div>

        {/* Validation Results */}
        {validations.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 mb-6">
            <div className="p-4 border-b border-slate-200">
              <h2 className="font-semibold text-slate-900">Validation Results</h2>
            </div>
            <div className="divide-y divide-slate-200">
              {validations.map((v, idx) => (
                <div key={idx} className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {v.passed ? (
                        <CheckCircle className="w-5 h-5 text-emerald-500" />
                      ) : (
                        <AlertTriangle className="w-5 h-5 text-red-500" />
                      )}
                      <div>
                        <div className="font-medium text-slate-900 capitalize">{v.validation_type}</div>
                        <div className="text-sm text-slate-500">{v.solution_id}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className="text-sm text-slate-500">Score</div>
                        <div className={`font-bold ${v.score >= 0.8 ? 'text-emerald-600' : v.score >= 0.5 ? 'text-amber-600' : 'text-red-600'}`}>
                          {(v.score * 100).toFixed(1)}%
                        </div>
                      </div>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${v.passed ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                        {v.passed ? 'PASSED' : 'FAILED'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Backtest Results */}
        {backtestResult && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200">
            <div className="p-4 border-b border-slate-200">
              <h2 className="font-semibold text-slate-900">Backtest Results</h2>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 bg-slate-50 rounded-lg">
                  <div className="text-sm text-slate-500">Period</div>
                  <div className="font-bold text-slate-900">{backtestResult.period || 'N/A'}</div>
                </div>
                <div className="p-4 bg-slate-50 rounded-lg">
                  <div className="text-sm text-slate-500">Sharpe Ratio</div>
                  <div className="font-bold text-slate-900">{backtestResult.sharpe_ratio?.toFixed(2) || 'N/A'}</div>
                </div>
                <div className="p-4 bg-slate-50 rounded-lg">
                  <div className="text-sm text-slate-500">Max Drawdown</div>
                  <div className="font-bold text-red-600">{backtestResult.max_drawdown ? `${(backtestResult.max_drawdown * 100).toFixed(1)}%` : 'N/A'}</div>
                </div>
                <div className="p-4 bg-slate-50 rounded-lg">
                  <div className="text-sm text-slate-500">Total Return</div>
                  <div className="font-bold text-emerald-600">{backtestResult.total_return ? `${(backtestResult.total_return * 100).toFixed(1)}%` : 'N/A'}</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
