import { Router } from "express";
import { demoController } from "../controllers/demo";
import { platformController } from "../controllers/platform";
import { authenticate } from "../middleware/auth";
import { requireOrganization } from "../middleware/tenant";

const router = Router();

router.use(authenticate, requireOrganization);

// Onboarding
router.get("/onboarding", (req, res, next) => platformController.getOnboarding(req, res).catch(next));

// Demo data
router.post("/demo/generate", (req, res, next) => platformController.loadDemo(req, res).catch(next));

// Compliance frameworks
router.get("/compliance/frameworks", (req, res, next) => platformController.getFrameworks(req, res).catch(next));
router.get("/compliance/frameworks/:id", (req, res, next) => platformController.getFrameworkDetail(req, res).catch(next));
router.get("/compliance/assessment", (req, res, next) => platformController.assessCompliance(req, res).catch(next));

// Subscription
router.get("/subscription", (req, res, next) => platformController.getSubscription(req, res).catch(next));
router.post("/subscription/checkout", (req, res, next) => platformController.createCheckout(req, res).catch(next));

// Blockchain integrations
router.post("/integrations/blockchain/validate", async (req, res, next) => {
  try {
    const { blockchainIngestionService } = await import("../services/blockchain");
    const valid = await blockchainIngestionService.validateAddress(req.body.address, req.body.chain);
    res.json({ success: true, data: { valid } });
  } catch (err) { next(err); }
});

export default router;

// Separate route for Stripe webhook (no auth)
import { Router as ERouter } from "express";
import express from "express";
export const stripeRouter = ERouter();
stripeRouter.post("/stripe/webhook", express.raw({ type: "application/json" }), (req, res, next) => platformController.stripeWebhook(req as any, res).catch(next));
