import { Queue, Worker } from "bullmq";
import { getRedis, isRedisAvailable } from "../config/redis";
import { config } from "../config";

function getQueue(name: string): Queue | null {
  if (!isRedisAvailable()) return null;
  return new Queue(name, {
    connection: getRedis(),
    defaultJobOptions: {
      attempts: 3,
      backoff: { type: "exponential", delay: 2000 },
      removeOnComplete: 100,
      removeOnFail: 50,
    },
  });
}

export const transactionQueue = getQueue("transaction-ingestion");
export const riskQueue = getQueue("risk-scoring");
export const webhookQueue = getQueue("webhook-delivery");
export const reportQueue = getQueue("report-generation");