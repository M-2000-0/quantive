import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

export const registerSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).max(128),
  name: z.string().min(1).max(255),
  organizationName: z.string().min(1).max(255),
});

export const refreshSchema = z.object({
  refreshToken: z.string().min(1),
});

export const createUserSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).max(128),
  name: z.string().min(1).max(255),
  roleId: z.string().uuid(),
});

export const updateUserSchema = z.object({
  name: z.string().min(1).max(255).optional(),
  isActive: z.boolean().optional(),
  roleId: z.string().uuid().optional(),
});
