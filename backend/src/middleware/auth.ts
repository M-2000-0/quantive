import { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import { config } from "../config";
import { prisma } from "../config/database";
import { AuthPayload, AuthenticatedRequest } from "../types";

const PUBLIC_ROUTES = [
  { method: "POST", path: "/api/v1/auth/login" },
  { method: "POST", path: "/api/v1/auth/register" },
  { method: "POST", path: "/api/v1/auth/refresh" },
  { method: "GET", path: "/api/v1/health" },
];

export async function authenticate(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): Promise<void> {
  const isPublic = PUBLIC_ROUTES.some(
    (route) => route.method === req.method && req.path === route.path
  );
  if (isPublic) return next();

  const authHeader = req.headers.authorization;
  if (!authHeader?.startsWith("Bearer ")) {
    res.status(401).json({ success: false, error: "Missing or invalid authorization header" });
    return;
  }

  const token = authHeader.split(" ")[1];
  try {
    const decoded = jwt.verify(token, config.jwt.secret) as AuthPayload;
    const user = await prisma.user.findUnique({
      where: { id: decoded.userId },
      select: { id: true, isActive: true, roleId: true },
    });

    if (!user || !user.isActive) {
      res.status(401).json({ success: false, error: "User not found or inactive" });
      return;
    }

    req.user = decoded;
    next();
  } catch {
    res.status(401).json({ success: false, error: "Invalid or expired token" });
  }
}
