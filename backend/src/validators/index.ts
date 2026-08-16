import { z } from "zod";

export const createAlertSchema = z.object({
  title: z.string().min(1).max(255),
  description: z.string().min(1),
  severity: z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
  reasonCode: z.string().min(1),
  transactionId: z.string().uuid().optional(),
  metadata: z.record(z.unknown()).optional(),
});

export const updateAlertSchema = z.object({
  status: z.enum(["OPEN", "ACKNOWLEDGED", "ESCALATED", "DISMISSED"]),
  dismissedReason: z.string().optional(),
});

export const alertQuerySchema = z.object({
  page: z.coerce.number().int().positive().default(1),
  limit: z.coerce.number().int().positive().max(100).default(20),
  sortBy: z.string().default("createdAt"),
  sortOrder: z.enum(["asc", "desc"]).default("desc"),
  status: z.enum(["OPEN", "ACKNOWLEDGED", "ESCALATED", "DISMISSED"]).optional(),
  severity: z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"]).optional(),
});

export const webhookCreateSchema = z.object({
  url: z.string().url(),
  events: z.array(z.string()).min(1),
  integrationId: z.string().uuid().optional(),
});
