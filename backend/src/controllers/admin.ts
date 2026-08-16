import { Response } from "express";
import { AuthenticatedRequest } from "../types";
import { auditService } from "../services/audit";
import { webhookService } from "../services/webhook";
import { userService } from "../services/user";
import { prisma } from "../config/database";
import { parsePagination } from "../utils/helpers";

export class AdminController {
  // Users
  async listUsers(req: AuthenticatedRequest, res: Response) {
    const result = await userService.listUsers(req.user!.organizationId, req.query);
    res.json({ success: true, ...result });
  }

  async createUser(req: AuthenticatedRequest, res: Response) {
    const user = await userService.createUser(req.user!.organizationId, req.body, req.traceId!, req.user!.userId);
    res.status(201).json({ success: true, data: user });
  }

  async updateUser(req: AuthenticatedRequest, res: Response) {
    const user = await userService.updateUser(req.user!.organizationId, String(req.params.id), req.body, req.traceId!, req.user!.userId);
    res.json({ success: true, data: user });
  }

  // Roles
  async listRoles(req: AuthenticatedRequest, res: Response) {
    const roles = await userService.listRoles(req.user!.organizationId);
    res.json({ success: true, data: roles });
  }

  async createRole(req: AuthenticatedRequest, res: Response) {
    const role = await userService.createRole(req.user!.organizationId, req.body);
    res.status(201).json({ success: true, data: role });
  }

  // Audit Logs
  async listAuditLogs(req: AuthenticatedRequest, res: Response) {
    const result = await auditService.list(req.user!.organizationId, req.query);
    res.json({ success: true, ...result });
  }

  // Webhooks
  async createWebhook(req: AuthenticatedRequest, res: Response) {
    const endpoint = await webhookService.createEndpoint(req.user!.organizationId, req.body);
    res.status(201).json({ success: true, data: { id: endpoint.id, url: endpoint.url, events: endpoint.events, isActive: endpoint.isActive } });
  }

  async listWebhooks(req: AuthenticatedRequest, res: Response) {
    const endpoints = await webhookService.listEndpoints(req.user!.organizationId);
    res.json({ success: true, data: endpoints });
  }

  async getWebhookDeliveries(req: AuthenticatedRequest, res: Response) {
    const deliveries = await webhookService.getDeliveries(String(req.params.id), req.user!.organizationId);
    res.json({ success: true, data: deliveries });
  }

  async deleteWebhook(req: AuthenticatedRequest, res: Response) {
    await webhookService.deleteEndpoint(req.user!.organizationId, String(req.params.id));
    res.json({ success: true, message: "Webhook endpoint deleted" });
  }

  // Integrations
  async listIntegrations(req: AuthenticatedRequest, res: Response) {
    const integrations = await prisma.integration.findMany({
      where: { organizationId: req.user!.organizationId },
    });
    res.json({ success: true, data: integrations });
  }

  async createIntegration(req: AuthenticatedRequest, res: Response) {
    const integration = await prisma.integration.create({
      data: {
        name: req.body.name,
        type: req.body.type,
        config: JSON.stringify(req.body.config || {}),
        organizationId: req.user!.organizationId,
      },
    });
    res.status(201).json({ success: true, data: integration });
  }

  // Organization settings
  async getOrganization(req: AuthenticatedRequest, res: Response) {
    const org = await prisma.organization.findUnique({
      where: { id: req.user!.organizationId },
      select: { id: true, name: true, slug: true, createdAt: true, _count: { select: { users: true, wallets: true, transactions: true, alerts: true, cases: true } } },
    });
    res.json({ success: true, data: org });
  }

  // Onboarding status
  async getOnboardingStatus(req: AuthenticatedRequest, res: Response) {
    const orgId = req.user!.organizationId;
    const [txCount, walletCount, userCount, integrationCount] = await Promise.all([
      prisma.transaction.count({ where: { organizationId: orgId } }),
      prisma.wallet.count({ where: { organizationId: orgId } }),
      prisma.user.count({ where: { organizationId: orgId } }),
      prisma.integration.count({ where: { organizationId: orgId } }),
    ]);
    const steps = [
      { id: "connect_data", label: "Connect a data source", done: integrationCount > 0 || txCount > 0 },
      { id: "explore_transactions", label: "Ingest transactions", done: txCount > 0 },
      { id: "invite_team", label: "Invite team members", done: userCount > 1 },
      { id: "review_alerts", label: "Review alerts", done: txCount > 0 },
    ];
    const complete = steps.every((s) => s.done);
    const progress = Math.round((steps.filter((s) => s.done).length / steps.length) * 100);
    res.json({ success: true, data: { steps, complete, progress } });
  }

  // Dashboard stats
  async getDashboardStats(req: AuthenticatedRequest, res: Response) {
    const orgId = req.user!.organizationId;
    const now = new Date();
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

    const [txCount, alertCount, caseCount, walletCount, recentTxs, alertsBySeverity, casesByStatus] = await Promise.all([
      prisma.transaction.count({ where: { organizationId: orgId } }),
      prisma.alert.count({ where: { organizationId: orgId, status: "OPEN" } }),
      prisma.case.count({ where: { organizationId: orgId, status: { in: ["OPEN", "UNDER_REVIEW"] } } }),
      prisma.wallet.count({ where: { organizationId: orgId } }),
      prisma.transaction.findMany({ where: { organizationId: orgId, timestamp: { gte: thirtyDaysAgo } }, orderBy: { timestamp: "desc" }, take: 10, select: { txHash: true, value: true, chain: true, riskLevel: true, timestamp: true } }),
      prisma.alert.groupBy({ by: ["severity"], where: { organizationId: orgId, createdAt: { gte: thirtyDaysAgo } }, _count: true }),
      prisma.case.groupBy({ by: ["status"], where: { organizationId: orgId }, _count: true }),
    ]);

    res.json({
      success: true,
      data: {
        overview: { totalTransactions: txCount, openAlerts: alertCount, activeCases: caseCount, totalWallets: walletCount },
        recentTransactions: recentTxs,
        alertsBySeverity,
        casesByStatus,
      },
    });
  }
}

export const adminController = new AdminController();
