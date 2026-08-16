import { Response } from "express";
import { AuthenticatedRequest } from "../types";
import { alertService } from "../services/alert";
import { prisma } from "../config/database";
import { parsePagination } from "../utils/helpers";

export class AlertController {
  async list(req: AuthenticatedRequest, res: Response) {
    const result = await alertService.listAlerts(req.user!.organizationId, req.query);
    res.json({ success: true, ...result });
  }

  async getById(req: AuthenticatedRequest, res: Response) {
    const alert = await prisma.alert.findFirst({
      where: { id: String(req.params.id), organizationId: req.user!.organizationId },
      include: {
        transaction: {
          select: { txHash: true, chain: true, timestamp: true, fromAddress: true, toAddress: true, value: true, riskScore: true, riskLevel: true },
        },
        case: { select: { id: true, title: true, status: true } },
      },
    });

    if (!alert) {
      res.status(404).json({ success: false, error: "Alert not found" });
      return;
    }

    res.json({ success: true, data: alert });
  }

  async updateStatus(req: AuthenticatedRequest, res: Response) {
    const { status, dismissedReason } = req.body;
    const result = await alertService.updateAlertStatus(
      req.user!.organizationId,
      String(req.params.id),
      status,
      req.traceId!,
      req.user!.userId,
      dismissedReason
    );
    res.json({ success: true, data: result });
  }
}

export const alertController = new AlertController();
