import { useEffect, useState } from 'react';
import { personalApi } from '../api';
import { ArrowUpDown, Filter, Tag, CheckCircle, XCircle } from 'lucide-react';

const TAX_TAGS: Record<string, { label: string; color: string }> = {
  'taxable-revenue': { label: 'Revenue', color: 'bg-emerald-900 text-emerald-300' },
  'revenue': { label: 'Revenue', color: 'bg-emerald-900 text-emerald-300' },
  'deductible': { label: 'Deductible', color: 'bg-blue-900 text-blue-300' },
  'tax-paid': { label: 'Tax Paid', color: 'bg-purple-900 text-purple-300' },
  'rental': { label: 'Rental', color: 'bg-sky-900 text-sky-300' },
  'non-deductible': { label: 'Personal', color: 'bg-zinc-800 text-zinc-400' },
  'review': { label: 'Needs Review', color: 'bg-sky-900 text-sky-300' },
};

export default function TransactionsPage() {
  const [txns, setTxns] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ category: '', tax_tag: '' });
  const [summary, setSummary] = useState<any>(null);

  useEffect(() => { loadTxns(); loadSummary(); }, [filter]);

  const loadTxns = async () => {
    setLoading(true);
    try {
      const data = await personalApi.transactions({ limit: 50, ...filter });
      setTxns(data.transactions || []);
      setTotal(data.total || 0);
    } catch {}
    setLoading(false);
  };

  const loadSummary = async () => {
    try { setSummary(await personalApi.transactionSummary()); } catch {}
  };

  const handleCategorize = async (id: string, tax_tag: string) => {
    await personalApi.categorizeTransaction(id, { tax_tag });
    loadTxns();
    loadSummary();
  };

  const formatAmount = (amt: number) => {
    const abs = Math.abs(amt / 100);
    const formatted = abs.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return amt < 0 ? `+$${formatted}` : `-$${formatted}`;
  };

  const categories = summary?.by_category?.map((c: any) => c.category).filter(Boolean) || [];
  const taxTags = summary?.by_tax_tag?.map((t: any) => t.tax_tag).filter(Boolean) || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Transactions</h1>
        <p className="text-zinc-400 mt-1">{total} transactions this year — categorized for tax optimization</p>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {summary.by_tax_tag.filter((t: any) => t.tax_tag !== 'non-deductible').slice(0, 4).map((t: any) => {
            const tag = TAX_TAGS[t.tax_tag] || { label: t.tax_tag, color: 'bg-zinc-800 text-zinc-300' };
            return (
              <div key={t.tax_tag} className="bg-zinc-900 rounded-lg border border-zinc-800 p-3">
                <p className="text-zinc-400 text-xs">{tag.label}</p>
                <p className="text-white font-semibold">${Math.abs(t.total / 100).toLocaleString()}</p>
                <p className="text-zinc-500 text-xs">{t.count} txns</p>
              </div>
            );
          })}
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3">
        <Filter className="w-4 h-4 text-zinc-400" />
        <select value={filter.tax_tag} onChange={(e) => setFilter({ ...filter, tax_tag: e.target.value })}
                className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-white">
          <option value="">All tax tags</option>
          {taxTags.map((t: string) => <option key={t} value={t}>{TAX_TAGS[t]?.label || t}</option>)}
        </select>
        <select value={filter.category} onChange={(e) => setFilter({ ...filter, category: e.target.value })}
                className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-white">
          <option value="">All categories</option>
          {categories.map((c: string) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {/* Transaction List */}
      {loading ? (
        <div className="text-zinc-400 py-8 text-center">Loading transactions...</div>
      ) : txns.length === 0 ? (
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-12 text-center">
          <p className="text-zinc-400">No transactions found. Connect a bank account to see transactions.</p>
        </div>
      ) : (
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-zinc-800">
                <th className="text-left px-4 py-3 text-zinc-400 text-sm font-medium">Date</th>
                <th className="text-left px-4 py-3 text-zinc-400 text-sm font-medium">Description</th>
                <th className="text-left px-4 py-3 text-zinc-400 text-sm font-medium">Category</th>
                <th className="text-left px-4 py-3 text-zinc-400 text-sm font-medium">Tax Tag</th>
                <th className="text-right px-4 py-3 text-zinc-400 text-sm font-medium">Amount</th>
                <th className="text-right px-4 py-3 text-zinc-400 text-sm font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {txns.map((txn) => {
                const tag = TAX_TAGS[txn.tax_tag] || { label: txn.tax_tag, color: 'bg-zinc-800 text-zinc-300' };
                return (
                  <tr key={txn.id} className={`border-b border-zinc-800/50 hover:bg-zinc-800/30 ${txn.excluded ? 'opacity-40' : ''}`}>
                    <td className="px-4 py-3 text-zinc-300 text-sm">{txn.date}</td>
                    <td className="px-4 py-3">
                      <p className="text-white text-sm">{txn.name}</p>
                      <p className="text-zinc-500 text-xs">{txn.merchant_name}</p>
                    </td>
                    <td className="px-4 py-3 text-zinc-300 text-sm capitalize">{txn.category}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-xs ${tag.color}`}>{tag.label}</span>
                    </td>
                    <td className={`px-4 py-3 text-right text-sm font-medium ${txn.amount < 0 ? 'text-emerald-400' : 'text-zinc-300'}`}>
                      {formatAmount(txn.amount)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {txn.tax_tag === 'review' && (
                        <div className="flex gap-1 justify-end">
                          <button onClick={() => handleCategorize(txn.id, 'deductible')}
                                  className="p-1 text-blue-400 hover:text-blue-300" title="Mark deductible">
                            <CheckCircle className="w-4 h-4" />
                          </button>
                          <button onClick={() => handleCategorize(txn.id, 'non-deductible')}
                                  className="p-1 text-zinc-400 hover:text-zinc-300" title="Mark non-deductible">
                            <XCircle className="w-4 h-4" />
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
