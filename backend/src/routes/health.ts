import { Router } from "express";
import { prisma } from "../config/database";

const router = Router();

router.get("/", async (_req, res) => {
  try {
    await prisma.$queryRaw`SELECT 1`;
    res.json({
      status: "healthy",
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
    });
  } catch {
    res.status(503).json({ status: "unhealthy", error: "Database connection failed" });
  }
});

export default router;
