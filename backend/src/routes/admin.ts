import { Router } from "express";
import { adminController } from "../controllers/admin";
import { authenticate } from "../middleware/auth";
import { requireOrganization } from "../middleware/tenant";
import { requirePermission } from "../middleware/rbac";
import { validate } from "../middleware/validation";
import { createUserSchema, updateUserSchema } from "../validators/auth";

const router = Router();

router.use(authenticate, requireOrganization);

// Organization
router.get("/organization", (req, res, next) => adminController.getOrganization(req, res).catch(next));
router.get("/dashboard", (req, res, next) => adminController.getDashboardStats(req, res).catch(next));
router.get("/onboarding", (req, res, next) => adminController.getOnboardingStatus(req, res).catch(next));

// Users
router.get("/users", requirePermission("users:read"), (req, res, next) => adminController.listUsers(req, res).catch(next));
router.post("/users", requirePermission("users:write"), validate(createUserSchema), (req, res, next) => adminController.createUser(req, res).catch(next));
router.patch("/users/:id", requirePermission("users:write"), validate(updateUserSchema), (req, res, next) => adminController.updateUser(req, res).catch(next));

// Roles
router.get("/roles", requirePermission("users:read"), (req, res, next) => adminController.listRoles(req, res).catch(next));
router.post("/roles", requirePermission("users:write"), (req, res, next) => adminController.createRole(req, res).catch(next));

// Audit Logs
router.get("/audit-logs", requirePermission("audit:read"), (req, res, next) => adminController.listAuditLogs(req, res).catch(next));

// Webhooks
router.get("/webhooks", requirePermission("integrations:read"), (req, res, next) => adminController.listWebhooks(req, res).catch(next));
router.post("/webhooks", requirePermission("integrations:write"), (req, res, next) => adminController.createWebhook(req, res).catch(next));
router.get("/webhooks/:id/deliveries", requirePermission("integrations:read"), (req, res, next) => adminController.getWebhookDeliveries(req, res).catch(next));
router.delete("/webhooks/:id", requirePermission("integrations:write"), (req, res, next) => adminController.deleteWebhook(req, res).catch(next));

// Integrations
router.get("/integrations", requirePermission("integrations:read"), (req, res, next) => adminController.listIntegrations(req, res).catch(next));
router.post("/integrations", requirePermission("integrations:write"), (req, res, next) => adminController.createIntegration(req, res).catch(next));

export default router;
