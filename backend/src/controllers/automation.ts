import { Response } from "express";
import { AuthenticatedRequest } from "../types";
import { automationService } from "../services/automation";

export class AutomationController {
  async listTemplates(req: AuthenticatedRequest, res: Response) {
    const templates = await automationService.listTemplates();
    res.json({ success: true, data: templates });
  }

  async getTemplate(req: AuthenticatedRequest, res: Response) {
    const template = await automationService.getTemplate(req.params.id as string);
    if (!template) {
      res.status(404).json({ success: false, error: "Template not found" });
      return;
    }
    res.json({ success: true, data: template });
  }

  async listActive(req: AuthenticatedRequest, res: Response) {
    const active = await automationService.listActive(req.user!.organizationId);
    res.json({ success: true, data: active });
  }

  async activate(req: AuthenticatedRequest, res: Response) {
    const { templateId, config } = req.body;
    const result = await automationService.activate(req.user!.organizationId, templateId, config);
    res.json({ success: true, data: result });
  }

  async deactivate(req: AuthenticatedRequest, res: Response) {
    await automationService.deactivate(req.user!.organizationId, req.params.id as string);
    res.json({ success: true, message: "Automation deactivated" });
  }

  async getWorkflowJson(req: AuthenticatedRequest, res: Response) {
    const json = automationService.getWorkflowJson(req.params.id as string);
    if (!json) {
      res.status(404).json({ success: false, error: "Workflow file not found" });
      return;
    }
    res.setHeader("Content-Type", "application/json");
    res.setHeader("Content-Disposition", `attachment; filename="${req.params.id}.json"`);
    res.send(json);
  }
}

export const automationController = new AutomationController();
