import { prisma } from "../config/database";
import { IngestedTransaction } from "../types";
import { riskService } from "./risk";
import { alertService } from "./alert";
import { logger } from "../config/logger";
import { auditService } from "./audit";

export class IngestionService {
  async ingestTransaction(
    organizationId: string,
    tx: IngestedTransaction,
    source: string,
    traceId: string,
    userId?: string
  ) {
    const existing = await prisma.transaction.findUnique({
      where: {
        organizationId_chain_txHash: {
          organizationId,
          chain: tx.chain,
          txHash: tx.txHash,
        },
      },
    });

    if (existing) {
      logger.warn({ txHash: tx.txHash, chain: tx.chain }, "Duplicate transaction skipped");
      return existing;
    }

    const timestamp = new Date(tx.timestamp);
    const value = typeof tx.value === "string" ? parseFloat(tx.value) : tx.value;

    const fromWallet = await this.upsertWallet(organizationId, tx.chain, tx.fromAddress);
    const toWallet = await this.upsertWallet(organizationId, tx.chain, tx.toAddress);

    const transaction = await prisma.transaction.create({
      data: {
        txHash: tx.txHash,
        chain: tx.chain,
        blockNumber: tx.blockNumber ? Number(tx.blockNumber) : null,
        timestamp,
        fromAddress: tx.fromAddress,
        toAddress: tx.toAddress,
        value,
        token: tx.token || null,
        tokenAmount: tx.tokenAmount ? parseFloat(tx.tokenAmount.toString()) : null,
        tokenDecimals: tx.tokenDecimals || null,
        gasUsed: tx.gasUsed ? Number(tx.gasUsed) : null,
        gasPrice: tx.gasPrice ? parseFloat(tx.gasPrice.toString()) : null,
        status: tx.status || "confirmed",
        rawData: tx.rawData ? JSON.stringify(tx.rawData) : undefined,
        riskReasonCodes: "[]",
        ingestedVia: source,
        organizationId,
        fromWalletId: fromWallet.id,
        toWalletId: toWallet.id,
      },
    });

    const riskResult = await riskService.scoreTransaction(organizationId, transaction, {
      fromWallet,
      toWallet,
    });

    await prisma.transaction.update({
      where: { id: transaction.id },
      data: {
        riskScore: riskResult.score,
        riskLevel: riskResult.level,
        riskReasonCodes: JSON.stringify(riskResult.reasonCodes),
      },
    });

    if (riskResult.level === "HIGH" || riskResult.level === "CRITICAL") {
      await alertService.createAlertFromRisk(organizationId, transaction.id, riskResult, traceId);
    }

    await auditService.log({
      organizationId,
      userId: userId || null,
      action: "CREATED",
      entityType: "transaction",
      entityId: transaction.id,
      description: `Transaction ${tx.txHash} ingested via ${source}`,
      metadata: { riskScore: riskResult.score, riskLevel: riskResult.level },
      traceId,
    });

    return transaction;
  }

  async ingestBatch(
    organizationId: string,
    transactions: IngestedTransaction[],
    source: string,
    traceId: string,
    userId?: string
  ) {
    const results = { ingested: 0, skipped: 0, errors: 0, details: [] as any[] };

    for (const tx of transactions) {
      try {
        await this.ingestTransaction(organizationId, tx, source, traceId, userId);
        results.ingested++;
      } catch (err: any) {
        if (err.code === "P2002") {
          results.skipped++;
          results.details.push({ txHash: tx.txHash, reason: "duplicate" });
        } else {
          results.errors++;
          results.details.push({ txHash: tx.txHash, reason: err.message });
          logger.error({ txHash: tx.txHash, error: err.message }, "Batch ingest error");
        }
      }
    }

    return results;
  }

  private async upsertWallet(organizationId: string, chain: string, address: string) {
    const existing = await prisma.wallet.findUnique({
      where: {
        organizationId_chain_address: { organizationId, chain, address },
      },
    });

    if (existing) {
      return prisma.wallet.update({
        where: { id: existing.id },
        data: { lastSeenAt: new Date() },
      });
    }

    return prisma.wallet.create({
      data: {
        address,
        chain,
        organizationId,
        tags: "[]",
        firstSeenAt: new Date(),
        lastSeenAt: new Date(),
      },
    });
  }
}

export const ingestionService = new IngestionService();
