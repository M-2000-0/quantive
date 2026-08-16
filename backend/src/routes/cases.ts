import { Router } from "express";
import { caseController } from "../controllers/case";
import { authenticate } from "../middleware/auth";
import { requireOrganization } from "../middleware/tenant";
import { requirePermission } from "../middleware/rbac";
import { validate } from "../middleware/validation";
import { createCaseSchema, updateCaseSchema, addCommentSchema, caseQuerySchema } from "../validators/case";

const router = Router();

router.use(authenticate, requireOrganization);

router.get("/", requirePermission("cases:read"), validate(caseQuerySchema, "query"), (req, res, next) => caseController.list(req, res).catch(next));
router.get("/:id", requirePermission("cases:read"), (req, res, next) => caseController.getById(req, res).catch(next));
router.post("/", requirePermission("cases:write"), validate(createCaseSchema), (req, res, next) => caseController.create(req, res).catch(next));
router.patch("/:id", requirePermission("cases:write", "cases:assign", "cases:close"), validate(updateCaseSchema), (req, res, next) => caseController.update(req, res).catch(next));
router.post("/:id/comments", requirePermission("cases:write"), validate(addCommentSchema), (req, res, next) => caseController.addComment(req, res).catch(next));

export default router;
