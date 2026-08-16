import { useEffect, useState } from "react";
import { api } from "../api/client";

interface ChainStatus {
  blockNumber: number;
  chainId: number;
  gasPrice: number;
}

interface Validator {
  address: string;
  total_stake: string;
  is_active: boolean;
}

export function BlockchainPage() {
  const [status, setStatus] = useState<ChainStatus | null>(null);
  const [validators, setValidators] = useState<Validator[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/blockchain/status").then((r: any) => {
      if (r?.success) setStatus(r.data);
      else setError(r?.error || "Failed to fetch chain status");
    });
    api.get("/blockchain/validators?epoch=0").then((r: any) => {
      if (r?.success) setValidators(r.data);
    });
  }, []);

  if (error) {
    return <div className="p-6 text-red-500">Error: {error}</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Omnichain Blockchain</h1>

      {status && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-sm text-gray-500">Block Height</div>
            <div className="text-2xl font-semibold">#{status.blockNumber}</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-sm text-gray-500">Chain ID</div>
            <div className="text-2xl font-semibold">{status.chainId}</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-sm text-gray-500">Gas Price</div>
            <div className="text-2xl font-semibold">{status.gasPrice.toLocaleString()} wei</div>
          </div>
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
        <h2 className="text-lg font-semibold mb-3">Validators (Epoch 0)</h2>
        {validators.length === 0 ? (
          <p className="text-gray-500">No validators registered yet</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b">
                <th className="pb-2">Address</th>
                <th className="pb-2">Total Stake</th>
                <th className="pb-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {validators.map((v, i) => (
                <tr key={i} className="border-b last:border-0">
                  <td className="py-2 font-mono">{v.address}</td>
                  <td className="py-2">{v.total_stake}</td>
                  <td className="py-2">{v.is_active ? "Active" : "Inactive"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
