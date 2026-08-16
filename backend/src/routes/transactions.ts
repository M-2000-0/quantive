import { Router } from "express";
import { transactionController } from "../controllers/transaction";
import { authenticate } from "../middleware/auth";
import { requireOrganization } from "../middleware/tenant";
import { requirePermission } from "../middleware/rbac";
import { validate } from "../middleware/validation";
import { ingestTransactionSchema, ingestBatchSchema, transactionQuerySchema } from "../validators/transaction";

const router = Router();

router.use(authenticate, requireOrganization);

router.get("/", validate(transactionQuerySchema, "query"), (req, res, next) => transactionController.list(req, res).catch(next));
router.get("/:id", (req, res, next) => transactionController.getById(req, res).catch(next));

router.post("/ingest", requirePermission("transactions:write"), validate(ingestTransactionSchema), (req, res, next) => transactionController.ingest(req, res).catch(next));
router.post("/ingest-batch", requirePermission("transactions:write"), validate(ingestBatchSchema), (req, res, next) => transactionController.ingestBatch(req, res).catch(next));

// Wallets
router.get("/wallets/list", requirePermission("wallets:read"), (req, res, next) => transactionController.listWallets(req, res).catch(next));
router.get("/wallets/:id", requirePermission("wallets:read"), (req, res, next) => transactionController.getWallet(req, res).catch(next));
router.patch("/wallets/:id/tags", requirePermission("wallets:write"), (req, res, next) => transactionController.updateWalletTags(req, res).catch(next));

export default router;
