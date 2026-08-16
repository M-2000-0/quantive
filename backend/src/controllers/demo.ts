import { Response } from "express";
import { AuthenticatedRequest } from "../types";
import { demoService } from "../services/demo";
import { auditService } from "../services/audit";

export class DemoController {
  async generate(req: AuthenticatedRequest, res: Response) {
    const result = await demoService.generateDemoData(req.user!.organizationId);
    await auditService.log({
      organizationId: req.user!.organizationId,
      userId: req.user!.userId,
      action: "UPDATED",
      entityType: "organization",
      entityId: req.user!.organizationId,
      description: "Demo data generated",
      metadata: result,
      traceId: req.traceId!,
    });
    res.json({ success: true, data: result });
  }
}

export const demoController = new DemoController();
