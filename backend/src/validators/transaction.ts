import { z } from "zod";

export const ingestTransactionSchema = z.object({
  txHash: z.string().min(1),
  chain: z.string().min(1),
  blockNumber: z.number().int().positive().optional(),
  timestamp: z.union([z.string(), z.number()]),
  fromAddress: z.string().min(1),
  toAddress: z.string().min(1),
  value: z.union([z.string(), z.number()]),
  token: z.string().optional(),
  tokenAmount: z.union([z.string(), z.number()]).optional(),
  tokenDecimals: z.number().int().optional(),
  gasUsed: z.number().int().optional(),
  gasPrice: z.union([z.string(), z.number()]).optional(),
  status: z.enum(["pending", "confirmed", "failed"]).optional(),
  rawData: z.record(z.unknown()).optional(),
});

export const ingestBatchSchema = z.object({
  transactions: z.array(ingestTransactionSchema).min(1).max(1000),
  source: z.enum(["api", "webhook", "csv"]),
});

export const transactionQuerySchema = z.object({
  page: z.coerce.number().int().positive().default(1),
  limit: z.coerce.number().int().positive().max(100).default(20),
  sortBy: z.string().default("timestamp"),
  sortOrder: z.enum(["asc", "desc"]).default("desc"),
  chain: z.string().optional(),
  fromAddress: z.string().optional(),
  toAddress: z.string().optional(),
  riskLevel: z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"]).optional(),
  startDate: z.string().optional(),
  endDate: z.string().optional(),
  minValue: z.coerce.number().optional(),
  maxValue: z.coerce.number().optional(),
});
