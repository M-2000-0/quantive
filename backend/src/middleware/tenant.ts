import { Response, NextFunction } from "express";
import { AuthenticatedRequest } from "../types";

export function requireOrganization(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): void {
  if (!req.user?.organizationId) {
    res.status(403).json({ success: false, error: "No organization context" });
    return;
  }

  const paramOrgId = req.params.organizationId || req.body.organizationId;
  if (paramOrgId && paramOrgId !== req.user.organizationId) {
    res.status(403).json({ success: false, error: "Cross-organization access denied" });
    return;
  }

  next();
}
