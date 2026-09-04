import React, { useState } from 'react';
import { Globe } from 'lucide-react';

interface CountryProfile {
  code: string;
  name: string;
  flag: string;
  debtGDP: number;
  deficitGDP: number;
  gdpGrowth: number;
  inflation: number;
  creditRating: string;
  cdsSpread: number;
  debtService: number;
  reserves: number;
  maturity: number;
  externalDebt: number;
}

const COUNTRIES: CountryProfile[] = [
  { code: 'US', name: 'United States', flag: '🇺🇸', debtGDP: 123.4, deficitGDP: -6.3, gdpGrowth: 2.1, inflation: 3.2, creditRating: 'AA+', cdsSpread: 35, debtService: 14.2, reserves: 0, maturity: 6.8, externalDebt: 98.2 },
  { code: 'MX', name: 'Mexico', flag: '🇲🇽', debtGDP: 52.8, deficitGDP: -3.5, gdpGrowth: 2.4, inflation: 4.8, creditRating: 'BBB', cdsSpread: 145, debtService: 18.5, reserves: 4.8, maturity: 7.2, externalDebt: 38.5 },
  { code: 'BR', name: 'Brazil', flag: '🇧🇷', debtGDP: 87.2, deficitGDP: -7.1, gdpGrowth: 1.8, inflation: 5.2, creditRating: 'BB-', cdsSpread: 215, debtService: 22.1, reserves: 12.5, maturity: 5.4, externalDebt: 32.1 },
  { code: 'CL', name: 'Chile', flag: '🇨🇱', debtGDP: 38.5, deficitGDP: -1.8, gdpGrowth: 2.8, inflation: 3.5, creditRating: 'A+', cdsSpread: 85, debtService: 12.3, reserves: 6.2, maturity: 8.1, externalDebt: 42.3 },
  { code: 'DE', name: 'Germany', flag: '🇩🇪', debtGDP: 66.2, deficitGDP: -2.1, gdpGrowth: 0.8, inflation: 2.4, creditRating: 'AAA', cdsSpread: 18, debtService: 8.5, reserves: 0, maturity: 7.5, externalDebt: 55.8 },
  { code: 'JP', name: 'Japan', flag: '🇯🇵', debtGDP: 264.2, deficitGDP: -4.2, gdpGrowth: 1.2, inflation: 2.8, creditRating: 'A+', cdsSpread: 42, debtService: 22.8, reserves: 22.5, maturity: 8.9, externalDebt: 18.2 },
  { code: 'GB', name: 'United Kingdom', flag: '🇬🇧', debtGDP: 98.3, deficitGDP: -4.5, gdpGrowth: 1.5, inflation: 3.8, creditRating: 'AA', cdsSpread: 52, debtService: 15.8, reserves: 2.8, maturity: 14.2, externalDebt: 315.2 },
  { code: 'FR', name: 'France', flag: '🇫🇷', debtGDP: 111.8, deficitGDP: -4.8, gdpGrowth: 1.1, inflation: 2.6, creditRating: 'AA', cdsSpread: 48, debtService: 16.2, reserves: 0, maturity: 8.8, externalDebt: 235.5 },
];

const METRICS = [
  { key: 'debtGDP', label: 'Debt/GDP', unit: '%', higherBetter: false },
  { key: 'deficitGDP', label: 'Deficit/GDP', unit: '%', higherBetter: true },
  { key: 'gdpGrowth', label: 'GDP Growth', unit: '%', higherBetter: true },
  { key: 'inflation', label: 'Inflation', unit: '%', higherBetter: false },
  { key: 'cdsSpread', label: 'CDS Spread', unit: 'bps', higherBetter: false },
  { key: 'debtService', label: 'Debt Service', unit: '% Rev', higherBetter: false },
  { key: 'maturity', label: 'Avg Maturity', unit: 'yr', higherBetter: true },
  { key: 'externalDebt', label: 'External Debt', unit: '% GDP', higherBetter: false },
];

export default function CrossCountryBenchmarking() {
  const [selectedCountry, setSelectedCountry] = useState<string>('MX');
  const [selectedMetric, setSelectedMetric] = useState<string>('debtGDP');
  const [sortBy, setSortBy] = useState<string>('debtGDP');

  const country = COUNTRIES.find(c => c.code === selectedCountry) || COUNTRIES[1];
  const metric = METRICS.find(m => m.key === selectedMetric) || METRICS[0];

  const sortedCountries = [...COUNTRIES].sort((a, b) => {
    const va = a[sortBy as keyof CountryProfile] as number;
    const vb = b[sortBy as keyof CountryProfile] as number;
    return metric.higherBetter ? vb - va : va - vb;
  });

  const maxVal = Math.max(...COUNTRIES.map(c => Math.abs(c[selectedMetric as keyof CountryProfile] as number)));

  const getRank = (code: string) => {
    return sortedCountries.findIndex(c => c.code === code) + 1;
  };

  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center">
          <Globe className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Cross-Country Benchmarking</h2>
          <p className="text-sm text-slate-400">Compare sovereign debt metrics against peer economies</p>
        </div>
      </div>

      {/* Country Selector */}
      <div className="flex gap-2 flex-wrap">
        {COUNTRIES.map(c => (
          <button
            key={c.code}
            onClick={() => setSelectedCountry(c.code)}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              selectedCountry === c.code
                ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                : 'bg-white/5 text-slate-400 hover:bg-white/10 border border-transparent'
            }`}
          >
            {c.flag} {c.name}
          </button>
        ))}
      </div>

      {/* Selected Country Overview */}
      <div className="glass rounded-2xl p-6">
        <div className="flex items-center gap-4 mb-4">
          <span className="text-4xl">{country.flag}</span>
          <div>
            <h3 className="text-xl font-bold text-white">{country.name}</h3>
            <span className={`px-3 py-1 rounded-lg text-xs font-medium ${
              country.creditRating.startsWith('AA') || country.creditRating === 'AAA' ? 'bg-green-500/20 text-green-400' :
              country.creditRating.startsWith('A') ? 'bg-blue-500/20 text-blue-400' :
              country.creditRating.startsWith('BBB') ? 'bg-yellow-500/20 text-yellow-400' :
              'bg-red-500/20 text-red-400'
            }`}>
              {country.creditRating}
            </span>
          </div>
          <div className="ml-auto text-right">
            <p className="text-sm text-slate-400">Regional Rank</p>
            <p className="text-2xl font-bold text-white">#{getRank(country.code)}</p>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-4">
          {METRICS.slice(0, 4).map(m => (
            <div key={m.key} className="bg-white/5 rounded-xl p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">{m.label}</p>
              <p className="text-xl font-bold text-white">
                {country[m.key as keyof CountryProfile]}{m.unit}
              </p>
              <p className="text-xs text-slate-500">
                Rank #{getRank(country.code)} of {COUNTRIES.length}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Metric Comparison */}
      <div className="glass rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-slate-400">COMPARISON: {metric.label.toUpperCase()}</h3>
          <select
            value={selectedMetric}
            onChange={(e) => { setSelectedMetric(e.target.value); setSortBy(e.target.value); }}
            className="px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-sm text-white focus:outline-none focus:border-blue-500/50"
          >
            {METRICS.map(m => (
              <option key={m.key} value={m.key}>{m.label} ({m.unit})</option>
            ))}
          </select>
        </div>

        <div className="space-y-3">
          {sortedCountries.map((c, i) => {
            const val = c[selectedMetric as keyof CountryProfile] as number;
            const barWidth = (Math.abs(val) / maxVal) * 100;
            const isBest = metric.higherBetter ? i === 0 : i === sortedCountries.length - 1;
            const isSelected = c.code === selectedCountry;

            return (
              <div key={c.code} className={`flex items-center gap-4 p-3 rounded-xl ${isSelected ? 'bg-blue-500/10 border border-blue-500/20' : 'bg-white/5'}`}>
                <span className="text-xs text-slate-500 w-6">#{i + 1}</span>
                <span className="text-lg">{c.flag}</span>
                <span className={`text-sm w-32 ${isSelected ? 'text-white font-medium' : 'text-slate-300'}`}>
                  {c.name}
                </span>
                <div className="flex-1 bg-white/5 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full transition-all ${
                      isBest ? 'bg-green-400' :
                      isSelected ? 'bg-blue-400' :
                      'bg-slate-500'
                    }`}
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
                <span className={`text-sm font-medium w-20 text-right ${isBest ? 'text-green-400' : 'text-white'}`}>
                  {val}{metric.unit}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* All Metrics Grid */}
      <div className="glass rounded-2xl p-6">
        <h3 className="text-sm font-medium text-slate-400 mb-4">FULL METRICS COMPARISON</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/10">
                <th className="text-left text-xs text-slate-500 py-2 px-3">Country</th>
                {METRICS.map(m => (
                  <th key={m.key} className="text-right text-xs text-slate-500 py-2 px-3 cursor-pointer hover:text-white"
                      onClick={() => setSortBy(m.key)}>
                    {m.label} {sortBy === m.key ? '↕' : ''}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {COUNTRIES.sort((a, b) => (a[selectedMetric as keyof CountryProfile] as number) - (b[selectedMetric as keyof CountryProfile] as number)).map(c => (
                <tr key={c.code} className={`border-b border-white/5 ${c.code === selectedCountry ? 'bg-blue-500/10' : 'hover:bg-white/5'}`}>
                  <td className="py-3 px-3">
                    <div className="flex items-center gap-2">
                      <span>{c.flag}</span>
                      <span className="text-sm text-white">{c.name}</span>
                    </div>
                  </td>
                  {METRICS.map(m => {
                    const val = c[m.key as keyof CountryProfile] as number;
                    const isBest = METRICS.indexOf(m) === 0;
                    return (
                      <td key={m.key} className="text-right py-3 px-3">
                        <span className={`text-sm ${c.code === selectedCountry ? 'text-blue-400 font-medium' : 'text-slate-300'}`}>
                          {val}{m.unit}
                        </span>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
