import { Request, Response, NextFunction } from "express";
import { v4 as uuidv4 } from "uuid";
import { AuthenticatedRequest } from "../types";

export function injectTraceId(
  req: AuthenticatedRequest,
  _res: Response,
  next: NextFunction
): void {
  req.traceId = (req.headers["x-trace-id"] as string) || uuidv4();
  next();
}
