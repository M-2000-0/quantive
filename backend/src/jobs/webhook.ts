import { Worker } from "bullmq";
import { getRedis, isRedisAvailable } from "../config/redis";
import { webhookService } from "../services/webhook";
import { logger } from "../config/logger";

export function startWebhookWorker() {
  if (!isRedisAvailable()) {
    logger.warn("Redis unavailable — webhook worker not started");
    return null;
  }
  const worker = new Worker(
    "webhook-delivery",
    async (job) => {
      const { organizationId, event, data } = job.data;
      return webhookService.dispatch(organizationId, event, data);
    },
    { connection: getRedis(), concurrency: 10 }
  );

  worker.on("completed", (job) => {
    logger.info({ jobId: job.id }, "Webhook job completed");
  });

  worker.on("failed", (job, err) => {
    logger.error({ jobId: job?.id, error: err.message }, "Webhook job failed");
  });

  return worker;
}