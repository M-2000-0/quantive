import { prisma } from "../config/database";
import bcrypt from "bcryptjs";

const CHAINS = ["ethereum", "solana", "polygon", "arbitrum", "bnb"];
const TOKENS = ["ETH", "USDC", "USDT", "SOL", "MATIC", "BNB", "ARB", "DAI", "LINK", "UNI"];
const WALLETS = [
  { address: "0x1234567890abcdef1234567890abcdef12345678", label: "Binance Cold Wallet", tags: ["exchange"] },
  { address: "0x2345678901abcdef2345678901abcdef23456789", label: "Coinbase Hot Wallet", tags: ["exchange"] },
  { address: "0x3456789012abcdef3456789012abcdef34567890", label: "Unknown Mixer", tags: ["mixer"] },
  { address: "0x4567890123abcdef4567890123abcdef45678901", label: "Sanctioned Address", tags: ["sanctioned"] },
  { address: "0x5678901234abcdef5678901234abcdef56789012", label: "Kraken Deposit", tags: ["exchange"] },
  { address: "0x6789012345abcdef6789012345abcdef67890123", label: "DeFi Protocol", tags: [] },
  { address: "0x7890123456abcdef7890123456abcdef78901234", label: "OTC Desk", tags: ["exchange"] },
  { address: "0x8901234567abcdef8901234567abcdef89012345", label: "Personal Wallet", tags: [] },
  { address: "0x9012345678abcdef9012345678abcdef90123456", label: "New Wallet", tags: [] },
  { address: "0x0123456789abcdef0123456789abcdef01234567", label: "Suspected Phishing", tags: ["scam"] },
];

export class DemoService {
  async generateDemoData(organizationId: string) {
    const existingTxs = await prisma.transaction.count({ where: { organizationId } });
    if (existingTxs > 50) return { message: "Demo data already exists", count: existingTxs };

    const now = Date.now();

    // Create wallets
    const walletRecords: any[] = [];
    for (const w of WALLETS) {
      const wallet = await prisma.wallet.upsert({
        where: { organizationId_chain_address: { organizationId, chain: "ethereum", address: w.address } },
        update: { tags: JSON.stringify(w.tags), label: w.label },
        create: {
          address: w.address,
          chain: "ethereum",
          label: w.label,
          tags: JSON.stringify(w.tags),
          riskScore: w.tags.includes("sanctioned") ? 0.95 : w.tags.includes("mixer") ? 0.85 : w.tags.includes("scam") ? 0.7 : Math.random() * 0.3,
          riskLevel: w.tags.includes("sanctioned") ? "CRITICAL" : w.tags.includes("mixer") ? "HIGH" : w.tags.includes("scam") ? "HIGH" : "LOW",
          organizationId,
        },
      });
      walletRecords.push(wallet);
    }

    // Generate 200 realistic transactions
    const transactions: any[] = [];
    for (let i = 0; i < 200; i++) {
      const from = walletRecords[Math.floor(Math.random() * walletRecords.length)];
      const to = walletRecords[Math.floor(Math.random() * walletRecords.length)];
      const value = Math.random() * 500;
      const chain = CHAINS[Math.floor(Math.random() * CHAINS.length)];
      const token = TOKENS[Math.floor(Math.random() * TOKENS.length)];
      const isRisky = from.tags.includes("sanctioned") || from.tags.includes("mixer") ||
                       to.tags.includes("sanctioned") || to.tags.includes("mixer");
      const riskScore = isRisky ? 0.5 + Math.random() * 0.5 : Math.random() * 0.4;
      const riskLevel = riskScore > 0.75 ? "CRITICAL" : riskScore > 0.5 ? "HIGH" : riskScore > 0.25 ? "MEDIUM" : "LOW";

      transactions.push({
        txHash: `0x${Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join("")}`,
        chain,
        blockNumber: 21000000 + i,
        timestamp: new Date(now - Math.random() * 30 * 24 * 60 * 60 * 1000),
        fromAddress: from.address,
        toAddress: to.address,
        value: parseFloat(value.toFixed(6)),
        token,
        tokenAmount: token === "ETH" || token === "SOL" || token === "MATIC" ? parseFloat(value.toFixed(6)) : parseFloat((value * Math.random() * 1000).toFixed(2)),
        tokenDecimals: token === "ETH" || token === "SOL" || token === "MATIC" ? 18 : 6,
        gasUsed: 21000 + Math.floor(Math.random() * 100000),
        gasPrice: parseFloat((Math.random() * 200 + 10).toFixed(0) + "000000000"),
        status: Math.random() > 0.05 ? "confirmed" : "failed",
        ingestedVia: "demo",
        organizationId,
        fromWalletId: from.id,
        toWalletId: to.id,
        riskScore: parseFloat(riskScore.toFixed(2)),
        riskLevel,
        riskReasonCodes: isRisky ? JSON.stringify(["SANCTIONED_ADDRESS", "HIGH_VALUE"]) : riskScore > 0.5 ? JSON.stringify(["HIGH_VALUE"]) : JSON.stringify([]),
      });
    }

    for (const tx of transactions) {
      await prisma.transaction.create({ data: tx });
    }

    // Generate 30 alerts from risky transactions
    const riskyTxs = await prisma.transaction.findMany({
      where: { organizationId, riskLevel: { in: ["HIGH", "CRITICAL"] } },
      take: 30,
      orderBy: { timestamp: "desc" },
    });

    for (const tx of riskyTxs) {
      const codes = JSON.parse(tx.riskReasonCodes || "[]");
      await prisma.alert.create({
        data: {
          title: `High-risk transaction detected: ${tx.txHash.slice(0, 10)}...`,
          description: `Transaction ${tx.txHash} scored ${tx.riskScore} (${tx.riskLevel}) on ${tx.chain}. Reason: ${codes.join(", ") || "HIGH_VALUE"}.`,
          severity: tx.riskLevel,
          status: Math.random() > 0.4 ? "OPEN" : Math.random() > 0.5 ? "ACKNOWLEDGED" : "DISMISSED",
          reasonCode: (JSON.parse(tx.riskReasonCodes || "[]"))[0] || "HIGH_VALUE",
          metadata: JSON.stringify({ simulated: true }),
          organizationId,
          transactionId: tx.id,
        },
      });
    }

    // Generate 8 cases with linked alerts
    const openAlerts = await prisma.alert.findMany({
      where: { organizationId, status: "OPEN" },
      take: 8,
    });

    for (let i = 0; i < Math.min(openAlerts.length, 8); i++) {
      const alert = openAlerts[i];
      const case_ = await prisma.case.create({
        data: {
          title: `Case #${i + 1}: ${alert.reasonCode.replace(/_/g, " ")} investigation`,
          description: `Investigating alert generated by transaction flagged as ${alert.severity} risk. Reason: ${alert.reasonCode}.`,
          status: i < 3 ? "OPEN" : i < 6 ? "UNDER_REVIEW" : "CLOSED",
          priority: alert.severity === "CRITICAL" ? "CRITICAL" : alert.severity === "HIGH" ? "HIGH" : "MEDIUM",
          riskLevel: alert.severity,
          findings: i < 6 ? null : "Transaction reviewed. No further suspicious activity detected from this wallet.",
          resolution: i < 6 ? null : "Closed after review. No action required.",
          closedAt: i < 6 ? null : new Date(),
          organizationId,
        },
      });

      await prisma.alert.update({
        where: { id: alert.id },
        data: { caseId: case_.id, status: "ESCALATED" },
      });
    }

    const counts = await Promise.all([
      prisma.transaction.count({ where: { organizationId } }),
      prisma.alert.count({ where: { organizationId } }),
      prisma.case.count({ where: { organizationId } }),
      prisma.wallet.count({ where: { organizationId } }),
    ]);

    return {
      message: "Demo data generated",
      wallets: counts[3],
      transactions: counts[0],
      alerts: counts[1],
      cases: counts[2],
    };
  }
}

export const demoService = new DemoService();
