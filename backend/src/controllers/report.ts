import { Response } from "express";
import { AuthenticatedRequest } from "../types";
import { reportService } from "../services/report";
import { reportQueue } from "../queues";

export class ReportController {
  async generate(req: AuthenticatedRequest, res: Response) {
    const { type, format, parameters } = req.body;

    if (format === "pdf") {
      const job = await reportQueue!.add("generate-report", {
        organizationId: req.user!.organizationId,
        type,
        format,
        parameters,
        traceId: req.traceId!,
        userId: req.user!.userId,
      });
      res.status(202).json({
        success: true,
        message: "Report generation queued",
        data: { jobId: job.id },
      });
      return;
    }

    const report = await reportService.generate(
      req.user!.organizationId,
      type,
      format,
      parameters,
      req.traceId!,
      req.user!.userId
    );
    res.status(201).json({ success: true, data: report });
  }

  async list(req: AuthenticatedRequest, res: Response) {
    const result = await reportService.list(req.user!.organizationId, req.query);
    res.json({ success: true, ...result });
  }
}

export const reportController = new ReportController();
