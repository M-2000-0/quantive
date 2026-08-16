import { Response, NextFunction } from "express";
import { AuthenticatedRequest } from "../types";

export function requirePermission(...permissions: string[]) {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction): void => {
    if (!req.user) {
      res.status(401).json({ success: false, error: "Unauthorized" });
      return;
    }

    const hasAll = permissions.every((p) => req.user!.permissions.includes(p));
    if (!hasAll) {
      res.status(403).json({ success: false, error: "Insufficient permissions" });
      return;
    }

    next();
  };
}
