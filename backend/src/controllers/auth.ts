import { Response } from "express";
import { authService } from "../services/auth";
import { auditService } from "../services/audit";
import { AuthenticatedRequest } from "../types";

export class AuthController {
  async register(req: AuthenticatedRequest, res: Response) {
    const result = await authService.register(req.body);
    await auditService.log({
      organizationId: result.user.organizationId,
      userId: result.user.id,
      action: "CREATED",
      entityType: "user",
      entityId: result.user.id,
      description: `User registered: ${result.user.email}`,
      traceId: req.traceId!,
      ipAddress: req.ip,
      userAgent: req.headers["user-agent"],
    });
    res.status(201).json({ success: true, data: result });
  }

  async login(req: AuthenticatedRequest, res: Response) {
    const { email, password } = req.body;
    const result = await authService.login(email, password);
    await auditService.log({
      organizationId: result.user.organizationId,
      userId: result.user.id,
      action: "LOGIN",
      entityType: "user",
      entityId: result.user.id,
      description: `User logged in: ${email}`,
      traceId: req.traceId!,
      ipAddress: req.ip,
      userAgent: req.headers["user-agent"],
    });
    res.json({ success: true, data: result });
  }

  async refresh(req: AuthenticatedRequest, res: Response) {
    const { refreshToken } = req.body;
    const tokens = await authService.refresh(refreshToken);
    res.json({ success: true, data: tokens });
  }

  async logout(req: AuthenticatedRequest, res: Response) {
    await authService.logout(req.user!.userId);
    await auditService.log({
      organizationId: req.user!.organizationId,
      userId: req.user!.userId,
      action: "LOGOUT",
      entityType: "user",
      entityId: req.user!.userId,
      description: "User logged out",
      traceId: req.traceId!,
    });
    res.json({ success: true, message: "Logged out" });
  }

  async me(req: AuthenticatedRequest, res: Response) {
    const user = await authService.getMe(req.user!.userId);
    res.json({ success: true, data: user });
  }
}

export const authController = new AuthController();
