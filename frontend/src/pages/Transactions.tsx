import { useEffect, useState } from "react";
import { api } from "../api/client";

export function TransactionsPage() {
  const [txs, setTxs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    setLoading(true);
    api.get(`/transactions?page=${page}&limit=25&sortBy=timestamp`).then((res) => {
      if (res?.success) {
        setTxs(res.data || []);
        setTotal(res.pagination?.total || 0);
      }
      setLoading(false);
    });
  }, [page]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-on-surface">Transactions</h2>
          <p className="text-xs text-on-muted mt-0.5">{total} total — Live monitoring</p>
        </div>
        <button className="text-xs text-on-variant border border-surface-variant rounded px-3 py-1.5 hover:bg-surface-high transition-colors" onClick={() => api.post("/demo/generate").then(() => window.location.reload())}>
          Load demo data
        </button>
      </div>

      <div className="bg-surface-container border border-surface-variant rounded-lg overflow-hidden">
        {loading ? (
          <p className="text-sm text-on-muted p-6 text-center">Loading...</p>
        ) : txs.length === 0 ? (
          <p className="text-sm text-on-muted p-6 text-center">No transactions found. Ingest data or load demo data to get started.</p>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="text-[10px] text-on-muted uppercase tracking-wider border-b border-surface-variant bg-surface-low">
                <th className="p-3 font-medium">Tx Hash</th>
                <th className="p-3 font-medium">From</th>
                <th className="p-3 font-medium">To</th>
                <th className="p-3 font-medium">Amount</th>
                <th className="p-3 font-medium">Chain</th>
                <th className="p-3 font-medium">Risk</th>
                <th className="p-3 font-medium">Time</th>
              </tr>
            </thead>
            <tbody>
              {txs.map((tx: any) => (
                <tr key={tx.id} className="border-b border-surface-variant/10 text-xs hover:bg-surface-low/50">
                  <td className="p-3 font-mono text-on-variant">{tx.txHash?.slice(0, 16)}...</td>
                  <td className="p-3 font-mono text-on-muted">{tx.fromAddress?.slice(0, 10)}...</td>
                  <td className="p-3 font-mono text-on-muted">{tx.toAddress?.slice(0, 10)}...</td>
                  <td className="p-3">{parseFloat(tx.value).toFixed(4)} {tx.token || "ETH"}</td>
                  <td className="p-3 text-on-variant">{tx.chain}</td>
                  <td className="p-3">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                      tx.riskLevel === "CRITICAL" ? "bg-error/20 text-error" :
                      tx.riskLevel === "HIGH" ? "bg-error/10 text-error" :
                      tx.riskLevel === "MEDIUM" ? "bg-primary/20 text-primary" :
                      "bg-surface-variant text-on-muted"
                    }`}>{tx.riskLevel}</span>
                  </td>
                  <td className="p-3 text-on-muted">{new Date(tx.timestamp).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {total > 25 && (
        <div className="flex items-center justify-between text-xs text-on-muted">
          <span>Page {page} of {Math.ceil(total / 25)}</span>
          <div className="flex gap-2">
            <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="px-2 py-1 border border-surface-variant rounded hover:bg-surface-high disabled:opacity-30">Previous</button>
            <button disabled={page >= Math.ceil(total / 25)} onClick={() => setPage(page + 1)} className="px-2 py-1 border border-surface-variant rounded hover:bg-surface-high disabled:opacity-30">Next</button>
          </div>
        </div>
      )}
    </div>
  );
}
