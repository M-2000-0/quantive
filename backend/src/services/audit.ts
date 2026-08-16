import { prisma } from "../config/database";

interface AuditLogInput {
  organizationId: string;
  userId: string | null;
  action: string;
  entityType: string;
  entityId: string;
  description: string;
  metadata?: Record<string, unknown>;
  traceId: string;
  ipAddress?: string;
  userAgent?: string;
  transactionId?: string;
  caseId?: string;
}

export class AuditService {
  async log(input: AuditLogInput) {
    return prisma.auditLog.create({
      data: {
        organizationId: input.organizationId,
        userId: input.userId,
        action: input.action,
        entityType: input.entityType,
        entityId: input.entityId,
        description: input.description,
        metadata: input.metadata ? JSON.stringify(input.metadata) : undefined,
        traceId: input.traceId,
        ipAddress: input.ipAddress || null,
        userAgent: input.userAgent || null,
        transactionId: input.transactionId || null,
        caseId: input.caseId || null,
      },
    });
  }

  async list(organizationId: string, query: any) {
    const p = Math.max(1, parseInt(query.page) || 1);
    const l = Math.min(Math.max(1, parseInt(query.limit) || 20), 100);
    const skip = (p - 1) * l;

    const where: any = { organizationId };
    if (query.action) where.action = query.action;
    if (query.entityType) where.entityType = query.entityType;
    if (query.entityId) where.entityId = query.entityId;

    const [data, total] = await Promise.all([
      prisma.auditLog.findMany({
        where,
        skip,
        take: l,
        orderBy: { createdAt: query.sortOrder || "desc" },
        include: {
          user: { select: { id: true, name: true, email: true } },
        },
      }),
      prisma.auditLog.count({ where }),
    ]);

    return { data, pagination: { page: p, limit: l, total, totalPages: Math.ceil(total / l) } };
  }
}

export const auditService = new AuditService();
