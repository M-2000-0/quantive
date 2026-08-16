import { config } from "./index";
import Redis from "ioredis";
import { logger } from "./logger";

let redis: Redis | null = null;
let _redisAvailable = false;

export function isRedisAvailable(): boolean {
  return _redisAvailable;
}

export function getRedis(): Redis {
  if (!redis) {
    redis = new Redis(config.redis.url, {
      maxRetriesPerRequest: 3,
      retryStrategy: (times: number) => Math.min(times * 100, 3000),
      lazyConnect: true,
      enableOfflineQueue: false,
    });
    redis.on("error", () => {});
  }
  return redis;
}

export async function connectRedis(): Promise<void> {
  try {
    const r = getRedis();
    if (r.status !== "ready" && r.status !== "connecting") {
      await r.connect();
    }
    _redisAvailable = true;
    logger.info("Connected to Redis");
  } catch (err) {
    _redisAvailable = false;
    logger.warn({ err }, "Redis not available — running without queues");
  }
}

export async function disconnectRedis(): Promise<void> {
  if (redis) {
    try { await redis.quit(); } catch { /* ignore */ }
    redis = null;
    _redisAvailable = false;
  }
}
