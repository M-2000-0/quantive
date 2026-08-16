import { prisma } from "../../config/database";
import { IngestedTransaction } from "../../types";
import { logger } from "../../config/logger";

export interface BlockchainSourceConfig {
  name: string;
  chain: string;
  rpcUrl?: string;
  apiKey?: string;
  webhookSecret?: string;
  pollingIntervalMs?: number;
}

export interface BlockchainAdapter {
  name: string;
  chain: string;
  fetchRecentTransactions(address: string, limit?: number): Promise<IngestedTransaction[]>;
  fetchTransactionByHash(txHash: string): Promise<IngestedTransaction | null>;
  validateAddress(address: string): boolean;
  healthCheck(): Promise<boolean>;
}

export class EtherscanAdapter implements BlockchainAdapter {
  name = "etherscan";
  chain = "ethereum";
  private apiKey: string;
  private baseUrl = "https://api.etherscan.io/api";

  constructor(config: BlockchainSourceConfig) {
    this.apiKey = config.apiKey || "";
  }

  validateAddress(address: string): boolean {
    return /^0x[a-fA-F0-9]{40}$/.test(address);
  }

  async healthCheck(): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}?module=proxy&action=eth_blockNumber&apikey=${this.apiKey}`);
      const data: any = await res.json();
      return data.result != null;
    } catch {
      return false;
    }
  }

  async fetchRecentTransactions(address: string, limit = 25): Promise<IngestedTransaction[]> {
    if (!this.validateAddress(address)) return [];
    try {
      const res = await fetch(
        `${this.baseUrl}?module=account&action=txlist&address=${address}&sort=desc&offset=${limit}&apikey=${this.apiKey}`
      );
      const data: any = await res.json();
      if (data.status !== "1" || !Array.isArray(data.result)) return [];

      return data.result.map((tx: any) => this.normalize(tx));
    } catch (err: any) {
      logger.error({ error: err.message, address }, "Etherscan fetch failed");
      return [];
    }
  }

  async fetchTransactionByHash(txHash: string): Promise<IngestedTransaction | null> {
    try {
      const res = await fetch(
        `${this.baseUrl}?module=proxy&action=eth_getTransactionByHash&txhash=${txHash}&apikey=${this.apiKey}`
      );
      const data: any = await res.json();
      if (!data.result) return null;
      return this.normalizeProxy(data.result);
    } catch {
      return null;
    }
  }

  private normalize(tx: any): IngestedTransaction {
    return {
      txHash: tx.hash,
      chain: "ethereum",
      blockNumber: parseInt(tx.blockNumber),
      timestamp: parseInt(tx.timeStamp) * 1000,
      fromAddress: tx.from.toLowerCase(),
      toAddress: (tx.to || "0x0000000000000000000000000000000000000000").toLowerCase(),
      value: parseFloat(tx.value) / 1e18,
      gasUsed: parseInt(tx.gasUsed),
      gasPrice: tx.gasPrice ? parseFloat(tx.gasPrice) : undefined,
      status: tx.isError === "0" ? "confirmed" : "failed",
      token: tx.tokenSymbol || undefined,
    };
  }

  private normalizeProxy(tx: any): IngestedTransaction {
    return {
      txHash: tx.hash,
      chain: "ethereum",
      fromAddress: (tx.from || "").toLowerCase(),
      toAddress: (tx.to || "").toLowerCase(),
      value: parseInt(tx.value || "0") / 1e18,
      timestamp: Date.now(),
    };
  }
}

export class AlchemyAdapter implements BlockchainAdapter {
  name = "alchemy";
  chain = "ethereum";
  private apiKey: string;
  private baseUrl: string;

  constructor(config: BlockchainSourceConfig) {
    this.apiKey = config.apiKey || "";
    this.baseUrl = `https://eth-mainnet.g.alchemy.com/v2/${this.apiKey}`;
  }

  validateAddress(address: string): boolean {
    return /^0x[a-fA-F0-9]{40}$/.test(address);
  }

  async healthCheck(): Promise<boolean> {
    try {
      const res = await fetch(this.baseUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_blockNumber", params: [] }),
      });
      const data: any = await res.json();
      return data.result != null;
    } catch {
      return false;
    }
  }

  async fetchRecentTransactions(address: string, limit = 25): Promise<IngestedTransaction[]> {
    try {
      const res = await fetch(this.baseUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jsonrpc: "2.0", id: 1, method: "alchemy_getAssetTransfers", params: [{
            fromBlock: "0x0", toBlock: "latest",
            fromAddress: address, category: ["external", "internal", "erc20", "erc721"],
            maxCount: limit, order: "desc",
          }],
        }),
      });
      const data: any = await res.json();
      if (!data.result?.transfers) return [];
      return data.result.transfers.map((tx: any) => this.normalize(tx));
    } catch (err: any) {
      logger.error({ error: err.message, address }, "Alchemy fetch failed");
      return [];
    }
  }

  async fetchTransactionByHash(txHash: string): Promise<IngestedTransaction | null> {
    try {
      const res = await fetch(this.baseUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_getTransactionByHash", params: [txHash] }),
      });
      const data: any = await res.json();
      if (!data.result) return null;
      return {
        txHash: data.result.hash,
        chain: "ethereum",
        fromAddress: (data.result.from || "").toLowerCase(),
        toAddress: (data.result.to || "").toLowerCase(),
        value: parseInt(data.result.value || "0") / 1e18,
        timestamp: Date.now(),
      };
    } catch {
      return null;
    }
  }

  private normalize(tx: any): IngestedTransaction {
    return {
      txHash: tx.hash,
      chain: "ethereum",
      fromAddress: (tx.from || "").toLowerCase(),
      toAddress: (tx.to || "").toLowerCase(),
      value: parseFloat(tx.value || "0"),
      token: tx.asset,
      tokenAmount: tx.value ? parseFloat(tx.value) : undefined,
      timestamp: new Date(tx.metadata?.blockTimestamp || Date.now()).getTime(),
    };
  }
}

export class OmnichainAdapter implements BlockchainAdapter {
  name = "omnichain";
  chain = "omnichain";
  private rpcUrl: string;

  constructor(config: BlockchainSourceConfig) {
    this.rpcUrl = config.rpcUrl || "http://127.0.0.1:8545";
  }

  validateAddress(address: string): boolean {
    return /^0x[a-fA-F0-9]{40}$/.test(address);
  }

  async healthCheck(): Promise<boolean> {
    try {
      const res = await fetch(this.rpcUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_blockNumber", params: [] }),
      });
      const data: any = await res.json();
      return data.result != null;
    } catch {
      return false;
    }
  }

  async fetchRecentTransactions(address: string, limit = 25): Promise<IngestedTransaction[]> {
    try {
      const res = await fetch(this.rpcUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jsonrpc: "2.0", id: 1, method: "eth_getBalance", params: [address, "latest"],
        }),
      });
      const data: any = await res.json();
      if (!data.result) return [];
      // Omnichain returns raw balance as hex; create a synthetic tx entry
      const balance = parseInt(data.result, 16);
      return [{
        txHash: `0x${"0".repeat(64)}`,
        chain: "omnichain",
        fromAddress: address,
        toAddress: address,
        value: balance / 1e18,
        timestamp: Date.now(),
      }];
    } catch {
      return [];
    }
  }

  async fetchTransactionByHash(txHash: string): Promise<IngestedTransaction | null> {
    try {
      const res = await fetch(this.rpcUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jsonrpc: "2.0", id: 1, method: "eth_getBalance", params: [txHash, "latest"],
        }),
      });
      const data: any = await res.json();
      if (!data.result) return null;
      return {
        txHash,
        chain: "omnichain",
        fromAddress: "0x0000000000000000000000000000000000000000",
        toAddress: "0x0000000000000000000000000000000000000000",
        value: 0,
        timestamp: Date.now(),
      };
    } catch {
      return null;
    }
  }

  // Omnichain-specific helpers
  async getBlockNumber(): Promise<number> {
    const res = await fetch(this.rpcUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_blockNumber", params: [] }),
    });
    const data: any = await res.json();
    return parseInt(data.result || "0x0", 16);
  }

  async getChainId(): Promise<number> {
    const res = await fetch(this.rpcUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_chainId", params: [] }),
    });
    const data: any = await res.json();
    return parseInt(data.result || "0x0", 16);
  }

  async getGasPrice(): Promise<number> {
    const res = await fetch(this.rpcUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_gasPrice", params: [] }),
    });
    const data: any = await res.json();
    return parseInt(data.result || "0x0", 16);
  }

  async getValidators(epoch: number): Promise<any[]> {
    const res = await fetch(this.rpcUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "omni_getValidators", params: [epoch] }),
    });
    const data: any = await res.json();
    try { return JSON.parse(data.result || "[]"); } catch { return []; }
  }

  async getMessageStatus(nonce: number): Promise<string> {
    const res = await fetch(this.rpcUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "omni_getMessageStatus", params: [nonce] }),
    });
    const data: any = await res.json();
    return data.result || "unknown";
  }

  async getBalance(address: string): Promise<string> {
    const res = await fetch(this.rpcUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_getBalance", params: [address, "latest"] }),
    });
    const data: any = await res.json();
    return data.result || "0x0";
  }
}

export function createBlockchainAdapter(config: BlockchainSourceConfig): BlockchainAdapter {
  const name = config.name.toLowerCase();
  if (name === "omnichain") return new OmnichainAdapter(config);
  if (name.includes("alchemy")) return new AlchemyAdapter(config);
  return new EtherscanAdapter(config);
}
