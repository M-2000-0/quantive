import { Response } from "express";
import { AuthenticatedRequest } from "../types";
import { ingestionService } from "../services/ingestion";
import { prisma } from "../config/database";
import { parsePagination } from "../utils/helpers";
import { transactionQueue } from "../queues";

export class TransactionController {
  async ingest(req: AuthenticatedRequest, res: Response) {
    const result = await ingestionService.ingestTransaction(
      req.user!.organizationId,
      req.body,
      "api",
      req.traceId!,
      req.user!.userId
    );
    res.status(201).json({ success: true, data: result });
  }

  async ingestBatch(req: AuthenticatedRequest, res: Response) {
    const { transactions, source } = req.body;

    if (transactions.length > 100) {
      const job = await transactionQueue!.add("batch-ingest", {
        organizationId: req.user!.organizationId,
        transactions,
        source: source || "api",
        traceId: req.traceId!,
        userId: req.user!.userId,
      });
      res.status(202).json({
        success: true,
        message: "Batch queued for processing",
        data: { jobId: job.id },
      });
      return;
    }

    const result = await ingestionService.ingestBatch(
      req.user!.organizationId,
      transactions,
      source || "api",
      req.traceId!,
      req.user!.userId
    );
    res.status(201).json({ success: true, data: result });
  }

  async list(req: AuthenticatedRequest, res: Response) {
    const pagination = parsePagination(req.query);
    const where: any = { organizationId: req.user!.organizationId };

    const q = req.query as Record<string, string>;
    if (q.chain) where.chain = q.chain;
    if (q.fromAddress) where.fromAddress = q.fromAddress;
    if (q.toAddress) where.toAddress = q.toAddress;
    if (q.riskLevel) where.riskLevel = q.riskLevel;
    if (q.startDate || q.endDate) {
      where.timestamp = {};
      if (q.startDate) where.timestamp.gte = new Date(q.startDate);
      if (q.endDate) where.timestamp.lte = new Date(q.endDate);
    }
    if (q.minValue || q.maxValue) {
      where.value = {};
      if (q.minValue) where.value.gte = parseFloat(q.minValue);
      if (q.maxValue) where.value.lte = parseFloat(q.maxValue);
    }

    const [data, total] = await Promise.all([
      prisma.transaction.findMany({
        where,
        skip: pagination.skip,
        take: pagination.limit,
        orderBy: { [pagination.sortBy]: pagination.sortOrder },
        include: {
          fromWallet: { select: { address: true, tags: true, riskLevel: true } },
          toWallet: { select: { address: true, tags: true, riskLevel: true } },
          alerts: { select: { id: true, severity: true, status: true, reasonCode: true } },
        },
      }),
      prisma.transaction.count({ where }),
    ]);

    res.json({
      success: true,
      data,
      pagination: {
        page: pagination.page,
        limit: pagination.limit,
        total,
        totalPages: Math.ceil(total / pagination.limit),
      },
    });
  }

  async getById(req: AuthenticatedRequest, res: Response) {
    const tx = await prisma.transaction.findFirst({
      where: { id: String(req.params.id), organizationId: req.user!.organizationId },
      include: {
        fromWallet: true,
        toWallet: true,
        alerts: { orderBy: { createdAt: "desc" } },
      },
    });

    if (!tx) {
      res.status(404).json({ success: false, error: "Transaction not found" });
      return;
    }

    res.json({ success: true, data: tx });
  }

  async listWallets(req: AuthenticatedRequest, res: Response) {
    const pagination = parsePagination(req.query);
    const where: any = { organizationId: req.user!.organizationId };

    const q2 = req.query as Record<string, string>;
    if (q2.chain) where.chain = q2.chain;
    if (q2.riskLevel) where.riskLevel = q2.riskLevel;
    if (q2.address) where.address = q2.address;

    const [data, total] = await Promise.all([
      prisma.wallet.findMany({
        where,
        skip: pagination.skip,
        take: pagination.limit,
        orderBy: { [pagination.sortBy]: pagination.sortOrder },
        include: {
          _count: { select: { transactionsFrom: true, transactionsTo: true } },
        },
      }),
      prisma.wallet.count({ where }),
    ]);

    res.json({
      success: true,
      data,
      pagination: { page: pagination.page, limit: pagination.limit, total, totalPages: Math.ceil(total / pagination.limit) },
    });
  }

  async getWallet(req: AuthenticatedRequest, res: Response) {
    const wallet = await prisma.wallet.findFirst({
      where: { id: String(req.params.id), organizationId: req.user!.organizationId },
      include: {
        _count: { select: { transactionsFrom: true, transactionsTo: true } },
        transactionsFrom: { orderBy: { timestamp: "desc" }, take: 20 },
        transactionsTo: { orderBy: { timestamp: "desc" }, take: 20 },
      },
    });

    if (!wallet) {
      res.status(404).json({ success: false, error: "Wallet not found" });
      return;
    }

    res.json({ success: true, data: wallet });
  }

  async updateWalletTags(req: AuthenticatedRequest, res: Response) {
    const { tags } = req.body;
    const wallet = await prisma.wallet.findFirst({
      where: { id: String(req.params.id), organizationId: req.user!.organizationId },
    });
    if (!wallet) {
      res.status(404).json({ success: false, error: "Wallet not found" });
      return;
    }

    const updated = await prisma.wallet.update({
      where: { id: wallet.id },
      data: { tags: JSON.stringify(tags) },
    });

    res.json({ success: true, data: updated });
  }
}

export const transactionController = new TransactionController();
