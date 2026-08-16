import { Router } from "express";
import { alertController } from "../controllers/alert";
import { authenticate } from "../middleware/auth";
import { requireOrganization } from "../middleware/tenant";
import { requirePermission } from "../middleware/rbac";
import { validate } from "../middleware/validation";
import { updateAlertSchema, alertQuerySchema } from "../validators";

const router = Router();

router.use(authenticate, requireOrganization);

router.get("/", requirePermission("alerts:read"), validate(alertQuerySchema, "query"), (req, res, next) => alertController.list(req, res).catch(next));
router.get("/:id", requirePermission("alerts:read"), (req, res, next) => alertController.getById(req, res).catch(next));
router.patch("/:id/status", requirePermission("alerts:write", "alerts:dismiss"), validate(updateAlertSchema), (req, res, next) => alertController.updateStatus(req, res).catch(next));

export default router;
