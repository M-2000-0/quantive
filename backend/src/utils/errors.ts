export class AppError extends Error {
  public statusCode: number;
  public code: string;

  constructor(message: string, statusCode: number, code: string) {
    super(message);
    this.statusCode = statusCode;
    this.code = code;
    this.name = "AppError";
  }
}

export const ErrorCodes = {
  VALIDATION_ERROR: "VALIDATION_ERROR",
  UNAUTHORIZED: "UNAUTHORIZED",
  FORBIDDEN: "FORBIDDEN",
  NOT_FOUND: "NOT_FOUND",
  CONFLICT: "CONFLICT",
  RATE_LIMITED: "RATE_LIMITED",
  INTERNAL_ERROR: "INTERNAL_ERROR",
  DUPLICATE_TRANSACTION: "DUPLICATE_TRANSACTION",
  INVALID_CREDENTIALS: "INVALID_CREDENTIALS",
  TOKEN_EXPIRED: "TOKEN_EXPIRED",
  ORGANIZATION_REQUIRED: "ORGANIZATION_REQUIRED",
  INTEGRATION_ERROR: "INTEGRATION_ERROR",
  WEBHOOK_FAILED: "WEBHOOK_FAILED",
  REPORT_FAILED: "REPORT_FAILED",
  CASE_NOT_FOUND: "CASE_NOT_FOUND",
  ALERT_NOT_FOUND: "ALERT_NOT_FOUND",
  TRANSACTION_NOT_FOUND: "TRANSACTION_NOT_FOUND",
  WALLET_NOT_FOUND: "WALLET_NOT_FOUND",
} as const;

export function badRequest(message: string, code = ErrorCodes.VALIDATION_ERROR) {
  return new AppError(message, 400, code);
}

export function unauthorized(message = "Unauthorized", code = ErrorCodes.UNAUTHORIZED) {
  return new AppError(message, 401, code);
}

export function forbidden(message = "Forbidden", code = ErrorCodes.FORBIDDEN) {
  return new AppError(message, 403, code);
}

export function notFound(message = "Resource not found", code = ErrorCodes.NOT_FOUND) {
  return new AppError(message, 404, code);
}

export function conflict(message = "Resource already exists", code = ErrorCodes.CONFLICT) {
  return new AppError(message, 409, code);
}

export function rateLimited(message = "Too many requests", code = ErrorCodes.RATE_LIMITED) {
  return new AppError(message, 429, code);
}
