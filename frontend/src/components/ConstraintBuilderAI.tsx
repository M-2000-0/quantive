import React, { useState } from 'react';

interface ParsedConstraint {
  id: string;
  naturalLanguage: string;
  mathematical: string;
  category: 'exposure' | 'risk' | 'liquidity' | 'regulatory' | 'esg' | 'custom';
  parameters: { name: string; value: string; unit: string }[];
  confidence: number;
  validation: 'valid' | 'warning' | 'error';
  validationMessage: string;
}

const PRESET_CONSTRAINTS: { text: string; category: string }[] = [
  { text: 'Keep USD exposure under 20%', category: 'exposure' },
  { text: 'Duration between 3 and 7 years', category: 'risk' },
  { text: 'At least 15% in green bonds', category: 'esg' },
  { text: 'No single counterparty above 10%', category: 'exposure' },
  { text: 'Minimum liquidity buffer of 20%', category: 'liquidity' },
  { text: 'Credit rating must be BBB+ or higher', category: 'regulatory' },
  { text: 'Max 5% in any single instrument', category: 'exposure' },
  { text: 'Total FX hedging cost under 2% of portfolio', category: 'risk' },
];

const CATEGORY_ICONS: Record<string, string> = {
  exposure: 'Target',
  risk: 'Scale',
  liquidity: '💧',
  regulatory: 'FileText',
  esg: '🌱',
  custom: '🔧'
};

export default function ConstraintBuilderAI() {
  const [input, setInput] = useState('');
  const [constraints, setConstraints] = useState<ParsedConstraint[]>([]);
  const [isParsing, setIsParsing] = useState(false);

  const parseConstraint = (text: string): ParsedConstraint => {
    const lower = text.toLowerCase();
    
    // Extract numbers
    const numbers = text.match(/\d+(\.\d+)?/g)?.map(Number) || [];
    const percent = text.includes('%');
    
    let category: ParsedConstraint['category'] = 'custom';
    let mathematical = '';
    let parameters: ParsedConstraint['parameters'] = [];
    let confidence = 85;
    let validation: ParsedConstraint['validation'] = 'valid';
    let validationMessage = '';

    // Parse exposure constraints
    if (lower.includes('exposure') || lower.includes('under') || lower.includes('above') || lower.includes('above')) {
      category = 'exposure';
      const currency = text.match(/\b(USD|EUR|GBP|JPY|CHF|AUD|CAD)\b/i)?.[1] || 'total';
      const limit = numbers[0] || 20;
      
      if (lower.includes('under') || lower.includes('below') || lower.includes('less than') || lower.includes('max')) {
        mathematical = `Σ(exposure_${currency}) / Portfolio ≤ ${limit}%`;
        parameters = [{ name: 'Currency', value: currency, unit: '' }, { name: 'Limit', value: String(limit), unit: '%' }];
      } else {
        mathematical = `Σ(exposure_${currency}) / Portfolio ≥ ${limit}%`;
        parameters = [{ name: 'Currency', value: currency, unit: '' }, { name: 'Minimum', value: String(limit), unit: '%' }];
      }
      confidence = 92;
    }
    
    // Parse duration constraints
    else if (lower.includes('duration')) {
      category = 'risk';
      if (numbers.length >= 2) {
        mathematical = `${numbers[0]} ≤ Duration ≤ ${numbers[1]}`;
        parameters = [{ name: 'Min', value: String(numbers[0]), unit: 'years' }, { name: 'Max', value: String(numbers[1]), unit: 'years' }];
      } else {
        const limit = numbers[0] || 5;
        mathematical = lower.includes('under') || lower.includes('below') ? `Duration ≤ ${limit}` : `Duration ≥ ${limit}`;
        parameters = [{ name: 'Target', value: String(limit), unit: 'years' }];
      }
      confidence = 94;
    }
    
    // Parse ESG constraints
    else if (lower.includes('green') || lower.includes('esg') || lower.includes('sustainable')) {
      category = 'esg';
      const limit = numbers[0] || 10;
      mathematical = `Σ(green_bonds) / Portfolio ≥ ${limit}%`;
      parameters = [{ name: 'Minimum', value: String(limit), unit: '%' }];
      confidence = 90;
    }
    
    // Parse liquidity constraints
    else if (lower.includes('liquidity') || lower.includes('buffer') || lower.includes('cash')) {
      category = 'liquidity';
      const limit = numbers[0] || 15;
      mathematical = `Σ(instruments_MATURITY_<1Y) / Portfolio ≥ ${limit}%`;
      parameters = [{ name: 'Buffer', value: String(limit), unit: '%' }];
      confidence = 88;
    }
    
    // Parse credit constraints
    else if (lower.includes('credit') || lower.includes('rating') || lower.includes('bbb') || lower.includes('aa')) {
      category = 'regulatory';
      const rating = text.match(/\b(AAA|AA\+|AA|AA-|A\+|A|A-|BBB\+|BBB|BBB-|BB\+|BB)\b/i)?.[1] || 'BBB+';
      mathematical = `credit_rating(instrument) ≥ ${rating}`;
      parameters = [{ name: 'Min Rating', value: rating, unit: '' }];
      confidence = 91;
    }
    
    // Parse counterparty constraints
    else if (lower.includes('counterparty') || lower.includes('issuer')) {
      category = 'exposure';
      const limit = numbers[0] || 10;
      mathematical = `max(exposure_issuer_i / Portfolio) ≤ ${limit}%`;
      parameters = [{ name: 'Max per Issuer', value: String(limit), unit: '%' }];
      confidence = 89;
    }
    
    // Parse cost constraints
    else if (lower.includes('cost') || lower.includes('expense') || lower.includes('hedging')) {
      category = 'risk';
      const limit = numbers[0] || 2;
      mathematical = `Σ(hedging_cost_i) / Portfolio ≤ ${limit}%`;
      parameters = [{ name: 'Max Cost', value: String(limit), unit: '%' }];
      confidence = 86;
    }
    
    else {
      mathematical = `Custom constraint: ${text}`;
      parameters = numbers.map((n, i) => ({ name: `Param ${i + 1}`, value: String(n), unit: percent ? '%' : '' }));
      confidence = 70;
      validation = 'warning';
      validationMessage = 'Could not fully parse this constraint. Please verify the mathematical formulation.';
    }

    return {
      id: `constraint-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      naturalLanguage: text,
      mathematical,
      category,
      parameters,
      confidence,
      validation,
      validationMessage
    };
  };

  const handleParse = (text?: string) => {
    const query = text || input;
    if (!query.trim()) return;
    
    setIsParsing(true);
    setTimeout(() => {
      const result = parseConstraint(query);
      setConstraints(prev => [result, ...prev]);
      setInput('');
      setIsParsing(false);
    }, 800);
  };

  const removeConstraint = (id: string) => {
    setConstraints(prev => prev.filter(c => c.id !== id));
  };

  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center">
          <span className="text-lg">✨</span>
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Constraint Builder AI</h2>
          <p className="text-sm text-slate-400">Describe constraints in plain English — AI converts them to mathematical formulations</p>
        </div>
      </div>

      {/* Input */}
      <div className="glass rounded-2xl p-4">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleParse()}
            placeholder="e.g., Keep USD exposure under 20%, Duration between 3 and 7 years..."
            className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/50 transition-colors"
          />
          <button
            onClick={() => handleParse()}
            disabled={isParsing || !input.trim()}
            className="px-6 py-3 bg-gradient-to-r from-emerald-500 to-teal-600 rounded-xl text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {isParsing ? 'Parsing...' : '✨ Parse'}
          </button>
        </div>

        {/* Presets */}
        <div className="mt-4">
          <p className="text-xs text-slate-500 mb-2">Quick constraints:</p>
          <div className="flex flex-wrap gap-2">
            {PRESET_CONSTRAINTS.map((p, i) => (
              <button
                key={i}
                onClick={() => {
                  setInput(p.text);
                  handleParse(p.text);
                }}
                className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-xs text-slate-300 hover:bg-white/10 transition-colors"
              >
                {CATEGORY_ICONS[p.category]} {p.text}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Parsing animation */}
      {isParsing && (
        <div className="glass rounded-xl p-4 text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }} />
            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }} />
          </div>
          <p className="text-slate-400 text-sm">Analyzing constraint and generating mathematical formulation...</p>
        </div>
      )}

      {/* Constraints List */}
      {constraints.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-slate-400">
              Active Constraints ({constraints.length})
            </h3>
            <button
              onClick={() => setConstraints([])}
              className="text-xs text-red-400 hover:text-red-300 transition-colors"
            >
              Clear All
            </button>
          </div>

          {constraints.map((c) => (
            <div key={c.id} className={`glass rounded-xl p-4 border-l-2 ${
              c.validation === 'valid' ? 'border-emerald-500' :
              c.validation === 'warning' ? 'border-yellow-500' : 'border-red-500'
            }`}>
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span>{CATEGORY_ICONS[c.category]}</span>
                  <span className="text-xs px-2 py-0.5 bg-white/10 rounded text-slate-400 capitalize">
                    {c.category}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    c.confidence >= 90 ? 'bg-green-500/20 text-green-400' :
                    c.confidence >= 75 ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-red-500/20 text-red-400'
                  }`}>
                    {c.confidence}% confidence
                  </span>
                  <button
                    onClick={() => removeConstraint(c.id)}
                    className="text-slate-500 hover:text-red-400 transition-colors"
                  >
                    ✕
                  </button>
                </div>
              </div>

              <p className="text-white text-sm mb-2">"{c.naturalLanguage}"</p>
              
              <div className="bg-white/5 rounded-lg p-3 mb-2">
                <p className="text-xs text-slate-500 mb-1">Mathematical Formulation:</p>
                <code className="text-emerald-400 text-sm font-mono">{c.mathematical}</code>
              </div>

              {c.parameters.length > 0 && (
                <div className="flex gap-3 mb-2">
                  {c.parameters.map((p, i) => (
                    <div key={i} className="text-xs">
                      <span className="text-slate-500">{p.name}: </span>
                      <span className="text-white">{p.value}{p.unit}</span>
                    </div>
                  ))}
                </div>
              )}

              {c.validation !== 'valid' && (
                <p className={`text-xs ${c.validation === 'warning' ? 'text-yellow-400' : 'text-red-400'}`}>
                  {c.validationMessage}
                </p>
              )}
            </div>
          ))}

          {/* Constraint Set Summary */}
          <div className="glass rounded-xl p-4">
            <h4 className="text-sm font-medium text-slate-400 mb-3">Constraint Set Summary</h4>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-2xl font-bold text-white">{constraints.length}</p>
                <p className="text-xs text-slate-500">Total Constraints</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-green-400">
                  {constraints.filter(c => c.validation === 'valid').length}
                </p>
                <p className="text-xs text-slate-500">Valid</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-yellow-400">
                  {constraints.filter(c => c.validation === 'warning').length}
                </p>
                <p className="text-xs text-slate-500">Warnings</p>
              </div>
            </div>
            <button className="w-full mt-4 py-2 bg-emerald-500/20 border border-emerald-500/30 rounded-xl text-emerald-400 text-sm font-medium hover:bg-emerald-500/30 transition-colors">
              Apply Constraint Set to Optimization →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
