import { Request, Response, NextFunction } from "express";
import { logger } from "../config/logger";
import { AuthenticatedRequest } from "../types";

export function requestLogger(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): void {
  const start = Date.now();

  res.on("finish", () => {
    const duration = Date.now() - start;
    logger.info(
      {
        traceId: req.traceId,
        method: req.method,
        path: req.path,
        statusCode: res.statusCode,
        duration: `${duration}ms`,
        userId: req.user?.userId,
        organizationId: req.user?.organizationId,
      },
      "Request completed"
    );
  });

  next();
}
