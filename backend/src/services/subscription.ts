import Stripe from "stripe";
import { prisma } from "../config/database";
import { logger } from "../config/logger";

// Real price IDs come from env; fall back to placeholders so the app boots in dev.
const PLANS = {
  starter: { priceId: process.env.STRIPE_PRICE_STARTER || "price_starter", monthlyCredits: 10000, name: "Starter" },
  business: { priceId: process.env.STRIPE_PRICE_BUSINESS || "price_business", monthlyCredits: 100000, name: "Business" },
  enterprise: { priceId: process.env.STRIPE_PRICE_ENTERPRISE || "price_enterprise", monthlyCredits: -1, name: "Enterprise" },
} as const;

export type PlanTier = keyof typeof PLANS;

export class SubscriptionService {
  private stripe: any;

  constructor() {
    this.stripe = new Stripe(process.env.STRIPE_SECRET_KEY || "sk_test_placeholder", {
      apiVersion: "2025-02-24.acacia" as any,
    });
  }

  verifyWebhookSignature(rawBody: Buffer | string, signature: string, secret: string) {
    // req.body is a Buffer because the route is mounted with express.raw().
    const payload = Buffer.isBuffer(rawBody) ? rawBody : Buffer.from(String(rawBody));
    return this.stripe.webhooks.constructEvent(payload, signature, secret);
  }

  private priceIdFor(plan: PlanTier): string {
    return PLANS[plan].priceId;
  }

  async createCheckoutSession(organizationId: string, plan: PlanTier, successUrl: string, cancelUrl: string) {
    const org = await prisma.organization.findUnique({ where: { id: organizationId } });
    if (!org) throw Object.assign(new Error("Organization not found"), { statusCode: 404 });

    const session = await this.stripe.checkout.sessions.create({
      mode: "subscription",
      payment_method_types: ["card"],
      line_items: [{ price: this.priceIdFor(plan), quantity: 1 }],
      client_reference_id: organizationId,
      success_url: successUrl,
      cancel_url: cancelUrl,
      metadata: { organizationId, plan },
    });

    // Record the pending subscription so billing state is real, not fabricated.
    await prisma.subscription.upsert({
      where: { id: org.id },
      update: {
        plan,
        status: "pending",
        stripePriceId: this.priceIdFor(plan),
        stripeSubId: null,
      },
      create: {
        id: org.id,
        organizationId,
        plan,
        status: "pending",
        stripePriceId: this.priceIdFor(plan),
      },
    });

    return { url: session.url, sessionId: session.id };
  }

  async handleWebhook(event: any) {
    switch (event.type) {
      case "checkout.session.completed": {
        const session = event.data.object;
        const orgId = session.metadata?.organizationId;
        const plan = session.metadata?.plan as PlanTier | undefined;
        if (orgId && plan && PLANS[plan]) {
          await prisma.subscription.upsert({
            where: { id: orgId },
            update: {
              plan,
              status: "active",
              stripeSubId: session.subscription || session.id,
              currentPeriodStart: new Date(),
            },
            create: {
              id: orgId,
              organizationId: orgId,
              plan,
              status: "active",
              stripeSubId: session.subscription || session.id,
              stripePriceId: this.priceIdFor(plan),
            },
          });
          logger.info({ orgId, plan }, "Subscription activated");
        }
        break;
      }
      case "customer.subscription.updated": {
        const sub = event.data.object;
        const orgId = sub.metadata?.organizationId || (await this.orgIdForSubscription(sub.id));
        if (!orgId) break;
        const status = sub.status === "active" ? "active" : sub.status === "past_due" ? "past_due" : "cancelled";
        await prisma.subscription.updateMany({
          where: { organizationId: orgId },
          data: {
            status,
            cancelAtPeriodEnd: !!sub.cancel_at_period_end,
            currentPeriodEnd: sub.current_period_end ? new Date(sub.current_period_end * 1000) : null,
          },
        });
        break;
      }
      case "invoice.payment_failed": {
        const invoice = event.data.object;
        logger.warn({ invoiceId: invoice.id }, "Payment failed");
        break;
      }
      case "customer.subscription.deleted": {
        const sub = event.data.object;
        const orgId = await this.orgIdForSubscription(sub.id);
        if (!orgId) break;
        await prisma.subscription.updateMany({
          where: { organizationId: orgId },
          data: { status: "cancelled", cancelAtPeriodEnd: false },
        });
        logger.info({ id: event.id, orgId }, "Subscription cancelled");
        break;
      }
    }
  }

  private async orgIdForSubscription(stripeSubId: string): Promise<string | null> {
    const found = await prisma.subscription.findFirst({
      where: { stripeSubId },
      select: { organizationId: true },
    });
    return found?.organizationId ?? null;
  }

  async getCurrentPlan(organizationId: string) {
    const sub = await prisma.subscription.findUnique({
      where: { id: organizationId },
      select: { plan: true, status: true },
    });
    if (!sub) return { plan: "starter" as PlanTier, status: "none", creditsUsed: 0, creditsLimit: PLANS.starter.monthlyCredits };
    return {
      plan: sub.plan as PlanTier,
      status: sub.status,
      creditsUsed: 0,
      creditsLimit: PLANS[sub.plan as PlanTier]?.monthlyCredits ?? 10000,
    };
  }

  async updatePlan(organizationId: string, plan: PlanTier) {
    const existing = await prisma.subscription.findUnique({ where: { id: organizationId } });
    if (!existing) {
      await prisma.subscription.create({
        data: { id: organizationId, organizationId, plan, status: "active", stripePriceId: this.priceIdFor(plan) },
      });
    } else {
      await prisma.subscription.update({
        where: { id: organizationId },
        data: { plan, status: existing.status === "pending" ? "active" : existing.status },
      });
    }
    return { plan, updatedAt: new Date().toISOString() };
  }
}

export const subscriptionService = new SubscriptionService();
