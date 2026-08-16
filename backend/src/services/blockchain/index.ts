import { prisma } from "../../config/database";
import { createBlockchainAdapter, BlockchainSourceConfig } from "./adapters";
import { ingestionService } from "../ingestion";
import { logger } from "../../config/logger";

export class BlockchainIngestionService {
  private activePolls: Map<string, NodeJS.Timeout> = new Map();

  async connectSource(organizationId: string, integrationId: string, config: BlockchainSourceConfig) {
    const adapter = createBlockchainAdapter(config);
    const healthy = await adapter.healthCheck();
    if (!healthy) {
      throw Object.assign(new Error(`Cannot connect to ${config.name}: health check failed`), { statusCode: 400 });
    }

    await prisma.integration.update({
      where: { id: integrationId },
      data: { status: "ACTIVE", lastSyncAt: new Date() },
    });

    return adapter;
  }

  async pollAddress(
    organizationId: string,
    integrationId: string,
    address: string,
    config: BlockchainSourceConfig
  ) {
    const adapter = createBlockchainAdapter(config);
    const txs = await adapter.fetchRecentTransactions(address, 25);
    if (txs.length === 0) return { ingested: 0 };

    const result = await ingestionService.ingestBatch(
      organizationId,
      txs,
      "api",
      `poll-${address.slice(0, 8)}`,
      undefined
    );

    await prisma.integration.update({
      where: { id: integrationId },
      data: { lastSyncAt: new Date() },
    });

    return result;
  }

  startPolling(
    organizationId: string,
    integrationId: string,
    address: string,
    config: BlockchainSourceConfig & { intervalMs?: number }
  ) {
    const key = `${organizationId}:${integrationId}:${address}`;
    if (this.activePolls.has(key)) return;

    const interval = config.intervalMs || 60_000;
    const poll = async () => {
      try {
        await this.pollAddress(organizationId, integrationId, address, config);
      } catch (err: any) {
        logger.error({ error: err.message, key }, "Polling error");
      }
    };

    poll();
    this.activePolls.set(key, setInterval(poll, interval));
    logger.info({ key, interval }, "Started polling blockchain address");
  }

  stopPolling(organizationId: string, integrationId: string, address: string) {
    const key = `${organizationId}:${integrationId}:${address}`;
    const timer = this.activePolls.get(key);
    if (timer) {
      clearInterval(timer);
      this.activePolls.delete(key);
      logger.info({ key }, "Stopped polling");
    }
  }

  async validateAddress(address: string, chain: string): Promise<boolean> {
    if (chain === "ethereum" || chain === "polygon" || chain === "arbitrum") {
      return /^0x[a-fA-F0-9]{40}$/.test(address);
    }
    if (chain === "solana") {
      return /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(address);
    }
    if (chain === "bitcoin") {
      return /^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$/.test(address) || /^bc1[a-z0-9]{39,59}$/.test(address);
    }
    return false;
  }
}

export const blockchainIngestionService = new BlockchainIngestionService();
