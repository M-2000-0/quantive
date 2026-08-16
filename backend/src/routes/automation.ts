import { Router } from "express";
import { automationController } from "../controllers/automation";
import { authenticate } from "../middleware/auth";
import { requireOrganization } from "../middleware/tenant";

const router = Router();

router.use(authenticate, requireOrganization);

router.get("/templates", (req, res, next) => automationController.listTemplates(req, res).catch(next));
router.get("/templates/:id", (req, res, next) => automationController.getTemplate(req, res).catch(next));
router.get("/active", (req, res, next) => automationController.listActive(req, res).catch(next));
router.post("/activate", (req, res, next) => automationController.activate(req, res).catch(next));
router.post("/:id/deactivate", (req, res, next) => automationController.deactivate(req, res).catch(next));
router.get("/workflow/:id", (req, res, next) => automationController.getWorkflowJson(req, res).catch(next));

export default router;
