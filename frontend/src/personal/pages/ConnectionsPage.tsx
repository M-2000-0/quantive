import { useEffect, useState } from 'react';
import { personalApi } from '../api';
import { Link2, RefreshCw, Unlink, Building2, CreditCard, Wallet, TrendingDown } from 'lucide-react';

export default function ConnectionsPage() {
  const [connections, setConnections] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    loadConnections();
  }, []);

  const loadConnections = async () => {
    try {
      const data = await personalApi.connections();
      setConnections(data.connections || []);
    } catch {}
    setLoading(false);
  };

  const handleConnect = async () => {
    setConnecting(true);
    try {
      const tokenData = await personalApi.createLinkToken();
      // In demo mode, directly exchange a demo token
      const result = await personalApi.exchangeToken(`demo-${Date.now()}`);
      await loadConnections();
    } catch (e) {
      console.error('Connection failed:', e);
    }
    setConnecting(false);
  };

  const handleSync = async (id: string) => {
    await personalApi.syncConnection(id);
    await loadConnections();
  };

  const handleDisconnect = async (id: string) => {
    if (confirm('Disconnect this account? Transactions will be preserved.')) {
      await personalApi.disconnectConnection(id);
      await loadConnections();
    }
  };

  const accountIcon = (type: string) => {
    switch (type) {
      case 'checking': return <Wallet className="w-5 h-5" />;
      case 'savings': return <Building2 className="w-5 h-5" />;
      case 'credit': return <CreditCard className="w-5 h-5" />;
      case 'investment': return <TrendingDown className="w-5 h-5" />;
      default: return <Building2 className="w-5 h-5" />;
    }
  };

  if (loading) return <div className="p-8 text-zinc-400">Loading connections...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Financial Connections</h1>
          <p className="text-zinc-400 mt-1">Connect bank accounts for real-time tax tracking</p>
        </div>
        <button onClick={handleConnect} disabled={connecting}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white rounded-lg text-sm font-medium flex items-center gap-2">
          <Link2 className="w-4 h-4" />
          {connecting ? 'Connecting...' : 'Connect Account'}
        </button>
      </div>

      {connections.length === 0 ? (
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-12 text-center">
          <Link2 className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No accounts connected</h3>
          <p className="text-zinc-400 mb-4">Connect your bank accounts to enable automatic transaction tracking and tax categorization.</p>
          <button onClick={handleConnect} disabled={connecting}
                  className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium">
            {connecting ? 'Connecting...' : 'Connect Your First Account'}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Accounts */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {connections.map((conn) => (
              <div key={conn.id} className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-zinc-800 rounded-lg text-zinc-300">
                      {accountIcon(conn.account_type)}
                    </div>
                    <div>
                      <h3 className="font-medium text-white">{conn.account_name}</h3>
                      <p className="text-zinc-400 text-sm">{conn.institution_name} ••{conn.account_mask}</p>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <button onClick={() => handleSync(conn.id)}
                            className="p-1.5 text-zinc-400 hover:text-white rounded"
                            title="Sync transactions">
                      <RefreshCw className="w-4 h-4" />
                    </button>
                    <button onClick={() => handleDisconnect(conn.id)}
                            className="p-1.5 text-zinc-400 hover:text-red-400 rounded"
                            title="Disconnect">
                      <Unlink className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-zinc-400">Balance</span>
                    <span className="text-white font-medium">
                      ${(conn.balance_current / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  {conn.balance_available !== conn.balance_current && (
                    <div className="flex justify-between text-sm">
                      <span className="text-zinc-400">Available</span>
                      <span className="text-zinc-300">
                        ${(conn.balance_available / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </span>
                    </div>
                  )}
                  {conn.last_sync && (
                    <div className="flex justify-between text-sm">
                      <span className="text-zinc-400">Last sync</span>
                      <span className="text-zinc-500">{new Date(conn.last_sync).toLocaleDateString()}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Info */}
          <div className="bg-zinc-900/50 rounded-lg border border-zinc-800 p-4">
            <p className="text-zinc-400 text-sm">
              <strong className="text-zinc-300">Demo Mode:</strong> Click "Connect Account" to add simulated bank accounts with realistic transaction data for testing.
              In production, this uses Plaid for secure bank connections.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
