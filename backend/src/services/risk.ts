import { prisma } from "../config/database";
import { RiskScoreResult } from "../types";

const RISK_RULES: Array<{
  code: string;
  description: string;
  score: number;
  evaluate: (tx: any, context: any) => boolean;
}> = [
  {
    code: "HIGH_VALUE",
    description: "Transaction value exceeds 100 ETH equivalent",
    score: 0.3,
    evaluate: (tx) => parseFloat(tx.value) > 100_000,
  },
  {
    code: "VERY_HIGH_VALUE",
    description: "Transaction value exceeds 1000 ETH equivalent",
    score: 0.6,
    evaluate: (tx) => parseFloat(tx.value) > 1_000_000,
  },
  {
    code: "NEW_WALLET_INTERACTION",
    description: "Interacting with a wallet first seen in the last 24 hours",
    score: 0.2,
    evaluate: (_tx, { fromWallet, toWallet }) => {
      const now = Date.now();
      const dayMs = 24 * 60 * 60 * 1000;
      return (
        (fromWallet && now - fromWallet.firstSeenAt.getTime() < dayMs) ||
        (toWallet && now - toWallet.firstSeenAt.getTime() < dayMs)
      );
    },
  },
  {
    code: "MIXER_INTERACTION",
    description: "Wallet tagged as mixer",
    score: 0.7,
    evaluate: (_tx, { fromWallet, toWallet }) => {
      return (
        fromWallet?.tags?.includes("mixer") || toWallet?.tags?.includes("mixer")
      );
    },
  },
  {
    code: "SANCTIONED_ADDRESS",
    description: "Wallet tagged as sanctioned",
    score: 0.9,
    evaluate: (_tx, { fromWallet, toWallet }) => {
      return (
        fromWallet?.tags?.includes("sanctioned") || toWallet?.tags?.includes("sanctioned")
      );
    },
  },
  {
    code: "EXCHANGE_WALLET",
    description: "Interaction with known exchange wallet",
    score: 0.1,
    evaluate: (_tx, { fromWallet, toWallet }) => {
      return (
        fromWallet?.tags?.includes("exchange") || toWallet?.tags?.includes("exchange")
      );
    },
  },
  {
    code: "RAPID_SUCCESSIVE_TXS",
    description: "Multiple rapid transactions from same wallet",
    score: 0.25,
    evaluate: (tx, _context) => {
      return false; // Would require DB query of recent txs from same address
    },
  },
  {
    code: "UNUSUAL_GAS_PRICE",
    description: "Gas price significantly deviates from average",
    score: 0.15,
    evaluate: (tx) => {
      if (!tx.gasPrice) return false;
      const gp = parseFloat(tx.gasPrice);
      return gp > 500_000_000_000 || gp < 1_000_000_000; // >500 gwei or <1 gwei
    },
  },
  {
    code: "ZERO_VALUE_TX",
    description: "Zero-value transaction (potential dusting)",
    score: 0.1,
    evaluate: (tx) => parseFloat(tx.value) === 0,
  },
  {
    code: "TOKEN_MISMATCH",
    description: "High-value token transfer with unusual parameters",
    score: 0.2,
    evaluate: (_tx, _context) => false,
  },
];

export class RiskService {
  async scoreTransaction(
    organizationId: string,
    transaction: any,
    context: { fromWallet?: any; toWallet?: any }
  ): Promise<RiskScoreResult> {
    const triggeredRules: string[] = [];
    let totalScore = 0;
    const details: Record<string, unknown> = {};

    for (const rule of RISK_RULES) {
      try {
        if (rule.evaluate(transaction, context)) {
          triggeredRules.push(rule.code);
          totalScore += rule.score;
          details[rule.code] = { score: rule.score, description: rule.description };
        }
      } catch (err) {
        // Skip rule on evaluation error
      }
    }

    totalScore = Math.min(totalScore, 1.0);

    let level: RiskScoreResult["level"] = "LOW";
    if (totalScore >= 0.75) level = "CRITICAL";
    else if (totalScore >= 0.5) level = "HIGH";
    else if (totalScore >= 0.25) level = "MEDIUM";

    return {
      score: Math.round(totalScore * 100) / 100,
      level,
      reasonCodes: triggeredRules,
      details,
    };
  }

  async scoreWallet(organizationId: string, walletId: string): Promise<RiskScoreResult> {
    const wallet = await prisma.wallet.findUnique({
      where: { id: walletId },
      include: {
        transactionsFrom: { orderBy: { timestamp: "desc" }, take: 100 },
        transactionsTo: { orderBy: { timestamp: "desc" }, take: 100 },
      },
    });

    if (!wallet) {
      throw Object.assign(new Error("Wallet not found"), { statusCode: 404 });
    }

    const allTxs = [...wallet.transactionsFrom, ...wallet.transactionsTo];
    const reasonCodes: string[] = [];
    let score = parseFloat(wallet.riskScore.toFixed(2));

    if (wallet.tags?.includes("sanctioned")) {
      score += 0.8;
      reasonCodes.push("SANCTIONED_ADDRESS");
    }
    if (wallet.tags?.includes("mixer")) {
      score += 0.6;
      reasonCodes.push("MIXER_INTERACTION");
    }
    if (allTxs.length > 100) {
      score += 0.15;
      reasonCodes.push("HIGH_TX_VOLUME");
    }
    if (wallet.tags?.length === 0 && allTxs.length === 0) {
      score += 0.05;
      reasonCodes.push("NEW_WALLET_NO_HISTORY");
    }

    score = Math.min(score, 1.0);

    let level: RiskScoreResult["level"] = "LOW";
    if (score >= 0.75) level = "CRITICAL";
    else if (score >= 0.5) level = "HIGH";
    else if (score >= 0.25) level = "MEDIUM";

    return {
      score: Math.round(score * 100) / 100,
      level,
      reasonCodes,
      details: { tagCount: wallet.tags.length, transactionCount: allTxs.length },
    };
  }
}

export const riskService = new RiskService();
