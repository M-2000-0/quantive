import { Worker } from "bullmq";
import { getRedis, isRedisAvailable } from "../config/redis";
import { reportService } from "../services/report";
import { logger } from "../config/logger";

export function startReportWorker() {
  if (!isRedisAvailable()) {
    logger.warn("Redis unavailable — report worker not started");
    return null;
  }
  const worker = new Worker(
    "report-generation",
    async (job) => {
      const { organizationId, type, format, parameters, traceId, userId } = job.data;
      return reportService.generate(organizationId, type, format, parameters, traceId, userId);
    },
    { connection: getRedis(), concurrency: 2 }
  );

  worker.on("completed", (job) => {
    logger.info({ jobId: job.id }, "Report generation job completed");
  });

  worker.on("failed", (job, err) => {
    logger.error({ jobId: job?.id, error: err.message }, "Report generation job failed");
  });

  return worker;
}