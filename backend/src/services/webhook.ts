import { prisma } from "../config/database";
import { logger } from "../config/logger";
import { encrypt, generateSecret } from "../utils/crypto";
import { config } from "../config";
import fetch from "node-fetch";

export class WebhookService {
  async dispatch(organizationId: string, event: string, data: Record<string, unknown>) {
    const endpoints = await prisma.webhookEndpoint.findMany({
      where: { organizationId, isActive: true },
    });

    for (const endpoint of endpoints) {
      await this.sendWithRetry(endpoint, event, data, organizationId);
    }
  }

  private async sendWithRetry(endpoint: any, event: string, data: Record<string, unknown>, organizationId: string) {
    const payload = {
      id: `${event}_${Date.now()}`,
      type: event,
      organizationId,
      data,
      timestamp: new Date().toISOString(),
    };

    let success = false;
    let statusCode: number | null = null;
    let responseBody: string | null = null;

    try {
      const response = await fetch(endpoint.url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Webhook-Secret": endpoint.secret,
          "X-Event-Type": event,
        },
        body: JSON.stringify(payload),
        timeout: 10000,
      });

      statusCode = response.status;
      responseBody = await response.text();
      success = response.status >= 200 && response.status < 300;
    } catch (err: any) {
      logger.error({ endpointId: endpoint.id, event, error: err.message }, "Webhook delivery failed");
    }

    await prisma.webhookDelivery.create({
      data: {
        endpointId: endpoint.id,
        event,
        payload: JSON.stringify(payload),
        status: statusCode,
        response: responseBody,
        success,
        attempt: endpoint.retryCount + 1,
        nextRetryAt: success ? null : new Date(Date.now() + config.webhook.retryDelayMs),
        deliveredAt: success ? new Date() : null,
      },
    });

    if (!success) {
      await prisma.webhookEndpoint.update({
        where: { id: endpoint.id },
        data: { retryCount: { increment: 1 }, lastTriggeredAt: new Date() },
      });

      if (endpoint.retryCount >= config.webhook.maxRetries) {
        await prisma.webhookEndpoint.update({
          where: { id: endpoint.id },
          data: { isActive: false, retryCount: 0 },
        });
        logger.warn({ endpointId: endpoint.id }, "Webhook deactivated after max retries");
      }
    }
  }

  async createEndpoint(organizationId: string, data: { url: string; events: string[]; integrationId?: string }) {
    const secret = generateSecret();
    return prisma.webhookEndpoint.create({
      data: {
        url: data.url,
        secret,
        events: JSON.stringify(data.events),
        organizationId,
        integrationId: data.integrationId || null,
      },
    });
  }

  async listEndpoints(organizationId: string) {
    return prisma.webhookEndpoint.findMany({
      where: { organizationId },
      include: { _count: { select: { deliveries: true } } },
    });
  }

  async getDeliveries(endpointId: string, organizationId: string) {
    return prisma.webhookDelivery.findMany({
      where: { endpointId, endpoint: { organizationId } },
      orderBy: { createdAt: "desc" },
      take: 50,
    });
  }

  async deleteEndpoint(organizationId: string, endpointId: string) {
    const ep = await prisma.webhookEndpoint.findFirst({
      where: { id: endpointId, organizationId },
    });
    if (!ep) throw Object.assign(new Error("Webhook endpoint not found"), { statusCode: 404 });

    await prisma.webhookDelivery.deleteMany({ where: { endpointId } });
    await prisma.webhookEndpoint.delete({ where: { id: endpointId } });
  }
}

export const webhookService = new WebhookService();
