import { prisma } from "../config/database";
import { auditService } from "./audit";
import { webhookService } from "./webhook";

export class CaseService {
  async create(
    organizationId: string,
    data: { title: string; description: string; priority?: string; alertIds?: string[] },
    traceId: string,
    userId: string
  ) {
    const case_ = await prisma.case.create({
      data: {
        title: data.title,
        description: data.description,
        priority: (data.priority as any) || "MEDIUM",
        organizationId,
        assigneeId: userId,
      },
    });

    if (data.alertIds?.length) {
      const riskLevels = await prisma.alert.findMany({
        where: { id: { in: data.alertIds }, organizationId },
        select: { id: true, severity: true },
      });

      await prisma.alert.updateMany({
        where: { id: { in: data.alertIds }, organizationId },
        data: { caseId: case_.id, status: "ESCALATED" },
      });

      const maxSeverity = riskLevels.reduce(
        (max, a) => (a.severity > max ? a.severity : max),
        "LOW" as any
      );
      await prisma.case.update({
        where: { id: case_.id },
        data: { riskLevel: maxSeverity },
      });

      await webhookService.dispatch(organizationId, "case.created", {
        caseId: case_.id,
        alertCount: data.alertIds.length,
        riskLevel: maxSeverity,
      });
    }

    await auditService.log({
      organizationId,
      userId,
      action: "CASE_CREATED",
      entityType: "case",
      entityId: case_.id,
      description: `Case created: ${data.title}`,
      metadata: { alertIds: data.alertIds, priority: data.priority },
      traceId,
      caseId: case_.id,
    });

    return case_;
  }

  async list(organizationId: string, query: any) {
    const { skip, take, page, limit } = this.parsePagination(query.page, query.limit);
    const where: any = { organizationId };

    if (query.status) where.status = query.status;
    if (query.priority) where.priority = query.priority;
    if (query.assigneeId) where.assigneeId = query.assigneeId;

    const [data, total] = await Promise.all([
      prisma.case.findMany({
        where,
        skip,
        take,
        orderBy: { [query.sortBy || "createdAt"]: query.sortOrder || "desc" },
        include: {
          assignee: { select: { id: true, name: true, email: true } },
          _count: { select: { alerts: true, comments: true } },
        },
      }),
      prisma.case.count({ where }),
    ]);

    return { data, pagination: { page, limit, total, totalPages: Math.ceil(total / limit) } };
  }

  async getById(organizationId: string, caseId: string) {
    const case_ = await prisma.case.findFirst({
      where: { id: caseId, organizationId },
      include: {
        assignee: { select: { id: true, name: true, email: true } },
        alerts: {
          orderBy: { createdAt: "desc" },
          include: {
            transaction: {
              select: { txHash: true, chain: true, value: true, fromAddress: true, toAddress: true, riskScore: true, riskLevel: true },
            },
          },
        },
        comments: {
          orderBy: { createdAt: "asc" },
          include: { author: { select: { id: true, name: true, email: true } } },
        },
      },
    });

    if (!case_) {
      throw Object.assign(new Error("Case not found"), { statusCode: 404 });
    }

    return case_;
  }

  async update(
    organizationId: string,
    caseId: string,
    data: any,
    traceId: string,
    userId: string
  ) {
    const existing = await prisma.case.findFirst({
      where: { id: caseId, organizationId },
    });
    if (!existing) {
      throw Object.assign(new Error("Case not found"), { statusCode: 404 });
    }

    const updated = await prisma.case.update({
      where: { id: caseId },
      data: {
        ...(data.title !== undefined && { title: data.title }),
        ...(data.description !== undefined && { description: data.description }),
        ...(data.status !== undefined && { status: data.status }),
        ...(data.priority !== undefined && { priority: data.priority }),
        ...(data.assigneeId !== undefined && { assigneeId: data.assigneeId }),
        ...(data.findings !== undefined && { findings: data.findings }),
        ...(data.resolution !== undefined && { resolution: data.resolution }),
        ...(data.status === "CLOSED" ? { closedAt: new Date() } : {}),
      },
    });

    if (data.status === "CLOSED" || data.status === "DISMISSED") {
      await prisma.alert.updateMany({
        where: { caseId, organizationId },
        data: { status: data.status === "CLOSED" ? "ACKNOWLEDGED" : "DISMISSED" },
      });
    }

    await auditService.log({
      organizationId,
      userId,
      action: data.status === "CLOSED" ? "CLOSED" : data.status === "DISMISSED" ? "DISMISSED" : "UPDATED",
      entityType: "case",
      entityId: caseId,
      description: `Case ${caseId} updated: ${Object.keys(data).join(", ")}`,
      metadata: { changes: data },
      traceId,
      caseId,
    });

    if (data.status === "CLOSED") {
      await webhookService.dispatch(organizationId, "case.closed", {
        caseId,
        resolution: data.resolution,
      });
    }

    return updated;
  }

  async addComment(
    organizationId: string,
    caseId: string,
    content: string,
    traceId: string,
    userId: string
  ) {
    const case_ = await prisma.case.findFirst({
      where: { id: caseId, organizationId },
    });
    if (!case_) {
      throw Object.assign(new Error("Case not found"), { statusCode: 404 });
    }

    const comment = await prisma.comment.create({
      data: { content, caseId, authorId: userId },
      include: { author: { select: { id: true, name: true, email: true } } },
    });

    await auditService.log({
      organizationId,
      userId,
      action: "COMMENTED",
      entityType: "case",
      entityId: caseId,
      description: "Comment added to case",
      metadata: { commentId: comment.id },
      traceId,
      caseId,
    });

    return comment;
  }

  private parsePagination(page: any, limit: any) {
    const p = Math.max(1, parseInt(page) || 1);
    const l = Math.min(Math.max(1, parseInt(limit) || 20), 100);
    return { skip: (p - 1) * l, take: l, page: p, limit: l };
  }
}

export const caseService = new CaseService();
