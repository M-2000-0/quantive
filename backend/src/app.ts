import express from "express";
import cors from "cors";
import helmet from "helmet";
import compression from "compression";
import cookieParser from "cookie-parser";
import rateLimit from "express-rate-limit";
import swaggerUi from "swagger-ui-express";
import openapi from "./config/openapi.json";
import { config } from "./config";
import { logger } from "./config/logger";
import { injectTraceId } from "./middleware/trace";
import { requestLogger } from "./middleware/logger";
import { errorHandler } from "./middleware/error";

import healthRoutes from "./routes/health";
import authRoutes from "./routes/auth";
import transactionRoutes from "./routes/transactions";
import alertRoutes from "./routes/alerts";
import caseRoutes from "./routes/cases";
import reportRoutes from "./routes/reports";
import adminRoutes from "./routes/admin";
import platformRoutes, { stripeRouter } from "./routes/platform";
import automationRoutes from "./routes/automation";
import blockchainRoutes from "./routes/blockchain";

const app = express();

const corsOrigin = config.isDev
  ? ["http://localhost:3000", "http://localhost:4000", "http://127.0.0.1:3000", "http://127.0.0.1:4000"]
  : process.env.CORS_ORIGIN?.split(",") || "https://quantive.io";

app.use(helmet({
  contentSecurityPolicy: false,
  crossOriginEmbedderPolicy: false,
}));
app.use(cors({ origin: corsOrigin, credentials: true, methods: ["GET", "POST", "PATCH", "DELETE"], allowedHeaders: ["Content-Type", "Authorization", "X-Trace-Id"] }));
app.use(compression());
app.use(cookieParser());
app.use(express.json({ limit: "10mb" }));
app.use(express.urlencoded({ extended: true }));

const limiter = rateLimit({
  windowMs: config.rateLimit.windowMs,
  max: config.rateLimit.max,
  standardHeaders: true,
  legacyHeaders: false,
  message: { success: false, error: "Too many requests, please try again later", code: "RATE_LIMITED" },
});
app.use(limiter);

app.use(injectTraceId);
app.use(requestLogger);

app.use("/api/v1/docs", swaggerUi.serve, swaggerUi.setup(openapi, { customSiteTitle: "Quantive API Docs" }));
app.use("/api/v1/health", healthRoutes);
const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 20,
  standardHeaders: true,
  legacyHeaders: false,
  message: { success: false, error: "Too many auth attempts, try again later", code: "RATE_LIMITED" },
});
app.use("/api/v1/auth", authLimiter, authRoutes);
app.use("/api/v1/transactions", transactionRoutes);
app.use("/api/v1/alerts", alertRoutes);
app.use("/api/v1/cases", caseRoutes);
app.use("/api/v1/reports", reportRoutes);
app.use("/api/v1/admin", adminRoutes);
app.use("/api/v1", platformRoutes);
app.use("/api/v1", stripeRouter);
app.use("/api/v1/automations", automationRoutes);
app.use("/api/v1/blockchain", blockchainRoutes);

app.use(errorHandler);

export default app;
