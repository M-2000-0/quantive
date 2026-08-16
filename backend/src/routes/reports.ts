import { Router } from "express";
import { reportController } from "../controllers/report";
import { authenticate } from "../middleware/auth";
import { requireOrganization } from "../middleware/tenant";
import { requirePermission } from "../middleware/rbac";

const router = Router();

router.use(authenticate, requireOrganization);

router.get("/", requirePermission("reports:read"), (req, res, next) => reportController.list(req, res).catch(next));
router.post("/generate", requirePermission("reports:write", "reports:export"), (req, res, next) => reportController.generate(req, res).catch(next));

export default router;
