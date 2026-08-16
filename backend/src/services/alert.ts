import { prisma } from "../config/database";
import { RiskScoreResult } from "../types";
import { auditService } from "./audit";
import { webhookService } from "./webhook";
import { logger } from "../config/logger";

export class AlertService {
  async createAlertFromRisk(
    organizationId: string,
    transactionId: string,
    riskResult: RiskScoreResult,
    traceId: string
  ) {
    const tx = await prisma.transaction.findUnique({
      where: { id: transactionId },
    });
    if (!tx) return null;

    const alert = await prisma.alert.create({
      data: {
        title: `High-risk transaction detected: ${tx.txHash.slice(0, 10)}...`,
        description: `Transaction ${tx.txHash} scored ${riskResult.score} (${riskResult.level}) on ${tx.chain}. Reasons: ${riskResult.reasonCodes.join(", ")}.`,
        severity: riskResult.level,
        reasonCode: riskResult.reasonCodes[0] || "UNKNOWN",
        metadata: JSON.stringify({ riskScore: riskResult.score, reasonCodes: riskResult.reasonCodes, details: riskResult.details }),
        organizationId,
        transactionId,
      },
    });

    await auditService.log({
      organizationId,
      userId: null,
      action: "ALERT_TRIGGERED",
      entityType: "alert",
      entityId: alert.id,
      description: `Alert created for tx ${tx.txHash}: ${riskResult.level} risk`,
      metadata: { riskScore: riskResult.score, reasonCodes: riskResult.reasonCodes },
      traceId,
      transactionId,
    });

    await webhookService.dispatch(organizationId, "alert.created", {
      alertId: alert.id,
      transactionId: tx.id,
      txHash: tx.txHash,
      riskLevel: riskResult.level,
      riskScore: riskResult.score,
      reasonCodes: riskResult.reasonCodes,
    });

    return alert;
  }

  async listAlerts(organizationId: string, query: any) {
    const { skip, take, page, limit } = this.parsePagination(query.page, query.limit);
    const where: any = { organizationId };

    if (query.status) where.status = query.status;
    if (query.severity) where.severity = query.severity;

    const [data, total] = await Promise.all([
      prisma.alert.findMany({
        where,
        skip,
        take,
        orderBy: { [query.sortBy || "createdAt"]: query.sortOrder || "desc" },
        include: {
          transaction: { select: { txHash: true, chain: true, value: true, fromAddress: true, toAddress: true } },
          case: { select: { id: true, title: true, status: true } },
        },
      }),
      prisma.alert.count({ where }),
    ]);

    return { data, pagination: { page, limit, total, totalPages: Math.ceil(total / limit) } };
  }

  async updateAlertStatus(
    organizationId: string,
    alertId: string,
    status: string,
    traceId: string,
    userId: string,
    dismissedReason?: string
  ) {
    const alert = await prisma.alert.findFirst({
      where: { id: alertId, organizationId },
    });
    if (!alert) {
      throw Object.assign(new Error("Alert not found"), { statusCode: 404 });
    }

    const updateData: any = { status };
    if (status === "ACKNOWLEDGED") {
      updateData.acknowledgedAt = new Date();
      updateData.acknowledgedBy = userId;
    } else if (status === "DISMISSED") {
      updateData.dismissedAt = new Date();
      updateData.dismissedBy = userId;
      updateData.dismissedReason = dismissedReason || null;
    }

    const updated = await prisma.alert.update({
      where: { id: alertId },
      data: updateData,
    });

    await auditService.log({
      organizationId,
      userId,
      action: "UPDATED",
      entityType: "alert",
      entityId: alertId,
      description: `Alert ${alertId} status changed to ${status}`,
      metadata: { previousStatus: alert.status, newStatus: status, dismissedReason },
      traceId,
    });

    return updated;
  }

  private parsePagination(page: any, limit: any) {
    const p = Math.max(1, parseInt(page) || 1);
    const l = Math.min(Math.max(1, parseInt(limit) || 20), 100);
    return { skip: (p - 1) * l, take: l, page: p, limit: l };
  }
}

export const alertService = new AlertService();
