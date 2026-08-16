import { Request } from "express";

export interface AuthPayload {
  userId: string;
  organizationId: string;
  roleId: string;
  permissions: string[];
}

export interface AuthenticatedRequest extends Request {
  user?: AuthPayload;
  traceId?: string;
}

export interface PaginationParams {
  page: number;
  limit: number;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  traceId?: string;
}

export interface RiskScoreResult {
  score: number;
  level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  reasonCodes: string[];
  details: Record<string, unknown>;
}

export interface IngestedTransaction {
  txHash: string;
  chain: string;
  blockNumber?: number;
  timestamp: string | number;
  fromAddress: string;
  toAddress: string;
  value: string | number;
  token?: string;
  tokenAmount?: string | number;
  tokenDecimals?: number;
  gasUsed?: number;
  gasPrice?: string | number;
  status?: string;
  rawData?: Record<string, unknown>;
}

export interface WebhookEvent {
  id: string;
  type: string;
  organizationId: string;
  data: Record<string, unknown>;
  timestamp: string;
}

export interface ReportParams {
  type: "case_summary" | "transaction_log" | "risk_overview" | "audit_trail";
  format: "csv" | "pdf";
  organizationId: string;
  filters?: Record<string, unknown>;
}
