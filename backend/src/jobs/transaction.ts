import { Worker } from "bullmq";
import { getRedis, isRedisAvailable } from "../config/redis";
import { ingestionService } from "../services/ingestion";
import { logger } from "../config/logger";

export function startTransactionWorker() {
  if (!isRedisAvailable()) {
    logger.warn("Redis unavailable — transaction worker not started");
    return null;
  }
  const worker = new Worker(
    "transaction-ingestion",
    async (job) => {
      const { organizationId, transactions, source, traceId, userId } = job.data;
      return ingestionService.ingestBatch(organizationId, transactions, source, traceId, userId);
    },
    { connection: getRedis(), concurrency: 5 }
  );

  worker.on("completed", (job) => {
    logger.info({ jobId: job.id }, "Transaction ingestion job completed");
  });

  worker.on("failed", (job, err) => {
    logger.error({ jobId: job?.id, error: err.message }, "Transaction ingestion job failed");
  });

  return worker;
}