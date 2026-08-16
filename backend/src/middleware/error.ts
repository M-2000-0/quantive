import { Request, Response, NextFunction } from "express";
import { logger } from "../config/logger";
import { AuthenticatedRequest } from "../types";
import { AppError } from "../utils/errors";

export function errorHandler(
  err: Error,
  req: AuthenticatedRequest,
  res: Response,
  _next: NextFunction
): void {
  const traceId = req.traceId || "unknown";

  if (err instanceof AppError) {
    logger.warn({ traceId, code: err.code, error: err.message, path: req.path }, "Application error");
    res.status(err.statusCode).json({
      success: false,
      error: err.message,
      code: err.code,
      traceId,
    });
    return;
  }

  logger.error(
    { traceId, error: err.message, stack: err.stack, path: req.path, method: req.method },
    "Unhandled error"
  );

  const statusCode = (err as any).statusCode || 500;
  const message =
    process.env.NODE_ENV === "production" && statusCode === 500
      ? "Internal server error"
      : err.message;

  res.status(statusCode).json({
    success: false,
    error: message,
    code: (err as any).code || "INTERNAL_ERROR",
    traceId,
  });
}
