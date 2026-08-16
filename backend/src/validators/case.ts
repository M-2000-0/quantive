import { z } from "zod";

export const createCaseSchema = z.object({
  title: z.string().min(1).max(255),
  description: z.string().min(1),
  priority: z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"]).default("MEDIUM"),
  alertIds: z.array(z.string().uuid()).optional(),
});

export const updateCaseSchema = z.object({
  title: z.string().min(1).max(255).optional(),
  description: z.string().min(1).optional(),
  status: z.enum(["OPEN", "UNDER_REVIEW", "ESCALATED", "CLOSED", "DISMISSED"]).optional(),
  priority: z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"]).optional(),
  assigneeId: z.string().uuid().nullable().optional(),
  findings: z.string().optional(),
  resolution: z.string().optional(),
});

export const addCommentSchema = z.object({
  content: z.string().min(1).max(5000),
});

export const caseQuerySchema = z.object({
  page: z.coerce.number().int().positive().default(1),
  limit: z.coerce.number().int().positive().max(100).default(20),
  sortBy: z.string().default("createdAt"),
  sortOrder: z.enum(["asc", "desc"]).default("desc"),
  status: z.enum(["OPEN", "UNDER_REVIEW", "ESCALATED", "CLOSED", "DISMISSED"]).optional(),
  priority: z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"]).optional(),
  assigneeId: z.string().uuid().optional(),
});
