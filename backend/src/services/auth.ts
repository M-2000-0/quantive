import bcrypt from "bcryptjs";
import jwt from "jsonwebtoken";
import { prisma } from "../config/database";
import { config } from "../config";
import { AuthPayload } from "../types";

const SALT_ROUNDS = 12;

export class AuthService {
  async register(data: { email: string; password: string; name: string; organizationName: string }) {
    const existing = await prisma.user.findUnique({ where: { email: data.email } });
    if (existing) {
      throw Object.assign(new Error("Email already registered"), { statusCode: 409 });
    }

    const passwordHash = await bcrypt.hash(data.password, SALT_ROUNDS);

    const org = await prisma.organization.create({
      data: { name: data.organizationName, slug: data.organizationName.toLowerCase().replace(/\s+/g, "-") },
    });

    const adminRole = await prisma.role.create({
      data: {
        name: "Admin",
        organizationId: org.id,
        isSystem: true,
        permissions: JSON.stringify([
          "users:read", "users:write", "users:delete",
          "transactions:read", "transactions:write",
          "wallets:read", "wallets:write",
          "alerts:read", "alerts:write", "alerts:dismiss",
          "cases:read", "cases:write", "cases:assign", "cases:close",
          "reports:read", "reports:write", "reports:export",
          "integrations:read", "integrations:write",
          "audit:read",
          "settings:read", "settings:write",
        ]),
      },
    });

    const user = await prisma.user.create({
      data: {
        email: data.email,
        passwordHash,
        name: data.name,
        organizationId: org.id,
        roleId: adminRole.id,
      },
      select: { id: true, email: true, name: true, organizationId: true, roleId: true },
    });

    const tokens = this.generateTokens({
      userId: user.id,
      organizationId: user.organizationId,
      roleId: user.roleId,
      permissions: JSON.parse(adminRole.permissions),
    });

    await prisma.user.update({
      where: { id: user.id },
      data: { refreshToken: tokens.refreshToken },
    });

    return { user, ...tokens };
  }

  async login(email: string, password: string) {
    const user = await prisma.user.findUnique({
      where: { email },
      include: { role: true },
    });

    if (!user || !user.isActive) {
      throw Object.assign(new Error("Invalid credentials"), { statusCode: 401 });
    }

    const valid = await bcrypt.compare(password, user.passwordHash);
    if (!valid) {
      throw Object.assign(new Error("Invalid credentials"), { statusCode: 401 });
    }

    const tokens = this.generateTokens({
      userId: user.id,
      organizationId: user.organizationId,
      roleId: user.roleId,
      permissions: JSON.parse(user.role.permissions),
    });

    await prisma.user.update({
      where: { id: user.id },
      data: { refreshToken: tokens.refreshToken, lastLoginAt: new Date() },
    });

    return {
      user: { id: user.id, email: user.email, name: user.name, role: user.role.name, organizationId: user.organizationId },
      ...tokens,
    };
  }

  async refresh(refreshToken: string) {
    try {
      const decoded = jwt.verify(refreshToken, config.jwt.refreshSecret) as AuthPayload;

      const user = await prisma.user.findUnique({
        where: { id: decoded.userId },
        include: { role: true },
      });

      if (!user || !user.isActive || user.refreshToken !== refreshToken) {
        throw Object.assign(new Error("Invalid refresh token"), { statusCode: 401 });
      }

      const tokens = this.generateTokens({
        userId: user.id,
        organizationId: user.organizationId,
        roleId: user.roleId,
        permissions: JSON.parse(user.role.permissions),
      });

      await prisma.user.update({
        where: { id: user.id },
        data: { refreshToken: tokens.refreshToken },
      });

      return tokens;
    } catch (err: any) {
      if (err.statusCode) throw err;
      throw Object.assign(new Error("Invalid refresh token"), { statusCode: 401 });
    }
  }

  async logout(userId: string) {
    await prisma.user.update({
      where: { id: userId },
      data: { refreshToken: null },
    });
  }

  async getMe(userId: string) {
    return prisma.user.findUnique({
      where: { id: userId },
      select: {
        id: true, email: true, name: true, avatarUrl: true,
        isActive: true, lastLoginAt: true, createdAt: true,
        role: { select: { id: true, name: true, permissions: true } },
        organization: { select: { id: true, name: true, slug: true } },
      },
    });
  }

  private generateTokens(payload: AuthPayload) {
    const accessToken = jwt.sign(payload, config.jwt.secret, {
      expiresIn: config.jwt.expiresIn as any,
    });
    const refreshToken = jwt.sign(payload, config.jwt.refreshSecret, {
      expiresIn: config.jwt.refreshExpiresIn as any,
    });
    return { accessToken, refreshToken };
  }
}

export const authService = new AuthService();
