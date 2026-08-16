import app from "./app";
import { config } from "./config";
import { logger } from "./config/logger";
import { prisma } from "./config/database";
import { connectRedis, disconnectRedis } from "./config/redis";
import { startTransactionWorker } from "./jobs/transaction";
import { startWebhookWorker } from "./jobs/webhook";
import { startReportWorker } from "./jobs/report";

async function main() {
  try {
    // Connect to PostgreSQL
    await prisma.$connect();
    logger.info("Connected to PostgreSQL");

    // Connect to Redis (optional — queues are skipped if unavailable)
    await connectRedis();

    // Start queue workers (only in non-test environments)
    if (config.nodeEnv !== "test") {
      startTransactionWorker();
      startWebhookWorker();
      startReportWorker();
      logger.info("Queue workers started");
    }

    // Start HTTP server
    app.listen(config.port, () => {
      logger.info({ port: config.port, env: config.nodeEnv }, "Quantive API server started");
    });
  } catch (err) {
    logger.error({ err }, "Failed to start server");
    process.exit(1);
  }
}

// Graceful shutdown
const shutdown = async () => {
  logger.info("Shutting down gracefully...");
  await prisma.$disconnect();
  await disconnectRedis();
  process.exit(0);
};

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

main();
