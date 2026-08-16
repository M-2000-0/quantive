import Stripe from "stripe";
import { prisma } from "../config/database";
import { config } from "../config";
import { logger } from "../config/logger";

const PLANS = {
  starter: { priceId: "price_starter", monthlyCredits: 10000, name: "Starter" },
  business: { priceId: "price_business", monthlyCredits: 100000, name: "Business" },
  enterprise: { priceId: "price_enterprise", monthlyCredits: -1, name: "Enterprise" },
} as const;

export type PlanTier = keyof typeof PLANS;

export class SubscriptionService {
  private stripe: any;

  constructor() {
    this.stripe = new Stripe(process.env.STRIPE_SECRET_KEY || "sk_test_placeholder", {
      apiVersion: "2025-02-24.acacia" as any,
    });
  }

  async createCheckoutSession(organizationId: string, plan: PlanTier, successUrl: string, cancelUrl: string) {
    const org = await prisma.organization.findUnique({ where: { id: organizationId } });
    if (!org) throw Object.assign(new Error("Organization not found"), { statusCode: 404 });

    const session = await this.stripe.checkout.sessions.create({
      mode: "subscription",
      payment_method_types: ["card"],
      line_items: [{ price: PLANS[plan].priceId, quantity: 1 }],
      client_reference_id: organizationId,
      success_url: successUrl,
      cancel_url: cancelUrl,
      metadata: { organizationId, plan },
    });

    return { url: session.url, sessionId: session.id };
  }

  async handleWebhook(event: any) {
    switch (event.type) {
      case "checkout.session.completed": {
        const session = event.data.object;
        const orgId = session.metadata?.organizationId;
        const plan = session.metadata?.plan as PlanTier;
        if (orgId && plan) {
          await prisma.organization.update({
            where: { id: orgId },
            data: {
              // In production, store subscription details in a Subscription model
            },
          });
          logger.info({ orgId, plan }, "Subscription activated");
        }
        break;
      }
      case "invoice.payment_failed": {
        const invoice = event.data.object;
        logger.warn({ invoiceId: invoice.id }, "Payment failed");
        break;
      }
      case "customer.subscription.deleted": {
        logger.info({ id: event.id }, "Subscription cancelled");
        break;
      }
    }
  }

  async getCurrentPlan(organizationId: string) {
    // In production, query the subscription table
    return { plan: "business" as PlanTier, status: "active", creditsUsed: 0, creditsLimit: 100000 };
  }

  async updatePlan(organizationId: string, plan: PlanTier) {
    return { plan, updatedAt: new Date().toISOString() };
  }
}

export const subscriptionService = new SubscriptionService();
