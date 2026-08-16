import { prisma } from "../config/database";
import { auditService } from "./audit";
import bcrypt from "bcryptjs";

export class UserService {
  async listUsers(organizationId: string, query: any) {
    const p = Math.max(1, parseInt(query.page) || 1);
    const l = Math.min(Math.max(1, parseInt(query.limit) || 20), 100);

    const [data, total] = await Promise.all([
      prisma.user.findMany({
        where: { organizationId },
        skip: (p - 1) * l,
        take: l,
        orderBy: { createdAt: "desc" },
        select: { id: true, email: true, name: true, avatarUrl: true, isActive: true, lastLoginAt: true, createdAt: true, role: { select: { id: true, name: true } } },
      }),
      prisma.user.count({ where: { organizationId } }),
    ]);

    return { data, pagination: { page: p, limit: l, total, totalPages: Math.ceil(total / l) } };
  }

  async createUser(organizationId: string, data: any, traceId: string, actorId: string) {
    const existing = await prisma.user.findUnique({ where: { email: data.email } });
    if (existing) {
      throw Object.assign(new Error("Email already in use"), { statusCode: 409 });
    }

    const passwordHash = await bcrypt.hash(data.password, 12);

    const user = await prisma.user.create({
      data: {
        email: data.email,
        passwordHash,
        name: data.name,
        organizationId,
        roleId: data.roleId,
      },
      select: { id: true, email: true, name: true, isActive: true, role: { select: { id: true, name: true } } },
    });

    await auditService.log({
      organizationId,
      userId: actorId,
      action: "CREATED",
      entityType: "user",
      entityId: user.id,
      description: `User created: ${data.email}`,
      traceId,
    });

    return user;
  }

  async updateUser(organizationId: string, userId: string, data: any, traceId: string, actorId: string) {
    const user = await prisma.user.findFirst({ where: { id: userId, organizationId } });
    if (!user) {
      throw Object.assign(new Error("User not found"), { statusCode: 404 });
    }

    const updated = await prisma.user.update({
      where: { id: userId },
      data: {
        ...(data.name !== undefined && { name: data.name }),
        ...(data.isActive !== undefined && { isActive: data.isActive }),
        ...(data.roleId !== undefined && { roleId: data.roleId }),
      },
      select: { id: true, email: true, name: true, isActive: true, role: { select: { id: true, name: true } } },
    });

    await auditService.log({
      organizationId,
      userId: actorId,
      action: "UPDATED",
      entityType: "user",
      entityId: userId,
      description: `User updated: ${data.name || data.email}`,
      metadata: { changes: data },
      traceId,
    });

    return updated;
  }

  async listRoles(organizationId: string) {
    return prisma.role.findMany({
      where: { organizationId },
      include: { _count: { select: { users: true } } },
    });
  }

  async createRole(organizationId: string, data: any) {
    const existing = await prisma.role.findUnique({
      where: { organizationId_name: { organizationId, name: data.name } },
    });
    if (existing) {
      throw Object.assign(new Error("Role name already exists"), { statusCode: 409 });
    }

    return prisma.role.create({
      data: {
        name: data.name,
        description: data.description || null,
        permissions: typeof data.permissions === "string" ? data.permissions : JSON.stringify(data.permissions),
        organizationId,
      },
    });
  }
}

export const userService = new UserService();
