import { Response } from "express";
import { AuthenticatedRequest } from "../types";
import { onboardingService } from "../services/onboarding";
import { complianceFrameworkService } from "../services/compliance";
import { subscriptionService } from "../services/subscription";

export class PlatformController {
  // Onboarding
  async getOnboarding(req: AuthenticatedRequest, res: Response) {
    const status = await onboardingService.getStatus(req.user!.organizationId);
    res.json({ success: true, data: status });
  }

  async loadDemo(req: AuthenticatedRequest, res: Response) {
    const result = await onboardingService.skipToDemo(req.user!.organizationId, req.traceId!, req.user!.userId);
    res.json({ success: true, data: result });
  }

  // Compliance frameworks
  async getFrameworks(req: AuthenticatedRequest, res: Response) {
    const frameworks = await complianceFrameworkService.getFrameworks();
    res.json({ success: true, data: frameworks });
  }

  async getFrameworkDetail(req: AuthenticatedRequest, res: Response) {
    const detail = await complianceFrameworkService.getFrameworkDetail(String(req.params.id));
    if (!detail) {
      res.status(404).json({ success: false, error: "Framework not found" });
      return;
    }
    res.json({ success: true, data: detail });
  }

  async assessCompliance(req: AuthenticatedRequest, res: Response) {
    const assessment = await complianceFrameworkService.assessOrganization(req.user!.organizationId);
    res.json({ success: true, data: assessment });
  }

  // Subscription
  async getSubscription(req: AuthenticatedRequest, res: Response) {
    const plan = await subscriptionService.getCurrentPlan(req.user!.organizationId);
    res.json({ success: true, data: plan });
  }

  async createCheckout(req: AuthenticatedRequest, res: Response) {
    const { plan, successUrl, cancelUrl } = req.body;
    const result = await subscriptionService.createCheckoutSession(req.user!.organizationId, plan, successUrl, cancelUrl);
    res.json({ success: true, data: result });
  }

  // Webhook handling (no auth)
  async stripeWebhook(req: AuthenticatedRequest, res: Response) {
    const sig = req.headers["stripe-signature"] as string;
    const secret = process.env.STRIPE_WEBHOOK_SECRET || "";
    if (!sig) {
      res.status(400).json({ success: false, error: "Missing stripe signature" });
      return;
    }
    if (!secret || secret.includes("placeholder")) {
      res.status(503).json({ success: false, error: "Stripe webhook secret not configured" });
      return;
    }
    let event: any;
    try {
      event = subscriptionService.verifyWebhookSignature(req.body, sig, secret);
    } catch (e: any) {
      res.status(400).json({ success: false, error: "Invalid stripe signature", detail: e?.message });
      return;
    }
    await subscriptionService.handleWebhook(event);
    res.json({ received: true });
  }
}

export const platformController = new PlatformController();
