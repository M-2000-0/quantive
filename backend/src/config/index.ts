import dotenv from "dotenv";
dotenv.config();

export const config = {
  port: parseInt(process.env.PORT || "4000", 10),
  nodeEnv: process.env.NODE_ENV || "development",
  isDev: (process.env.NODE_ENV || "development") === "development",

  database: {
    url: process.env.DATABASE_URL || "postgresql://quantive:quantive@localhost:5432/quantive",
  },

  redis: {
    url: process.env.REDIS_URL || "redis://localhost:6379",
  },

  jwt: {
    secret: process.env.JWT_SECRET || "",
    refreshSecret: process.env.JWT_REFRESH_SECRET || "",
    expiresIn: process.env.JWT_EXPIRES_IN || "15m",
    refreshExpiresIn: process.env.JWT_REFRESH_EXPIRES_IN || "7d",
  },

  s3: {
    endpoint: process.env.S3_ENDPOINT || "http://localhost:9000",
    region: process.env.S3_REGION || "us-east-1",
    accessKey: process.env.S3_ACCESS_KEY || "",
    secretKey: process.env.S3_SECRET_KEY || "",
    bucket: process.env.S3_BUCKET || "quantive-reports",
  },

  encryption: {
    key: process.env.ENCRYPTION_KEY || "",
  },

  rateLimit: {
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || "900000", 10),
    max: parseInt(process.env.RATE_LIMIT_MAX || "100", 10),
  },

  logging: {
    level: process.env.LOG_LEVEL || "info",
  },

  webhook: {
    maxRetries: parseInt(process.env.WEBHOOK_MAX_RETRIES || "5", 10),
    retryDelayMs: parseInt(process.env.WEBHOOK_RETRY_DELAY_MS || "60000", 10),
  },

  supabase: {
    url: process.env.SUPABASE_URL || "",
    serviceKey: process.env.SUPABASE_SERVICE_KEY || "",
  },
} as const;
