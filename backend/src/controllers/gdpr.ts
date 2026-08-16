import { Response } from "express";
import { AuthenticatedRequest } from "../types";
import { deleteOrganizationData, exportOrganizationData } from "../services/gdpr";

export class GdprController {
  async erase(req: AuthenticatedRequest, res: Response) {
    const receipt = await deleteOrganizationData(req.user!.organizationId);
    res.json({ success: true, data: receipt });
  }

  async exportData(req: AuthenticatedRequest, res: Response) {
    const data = await exportOrganizationData(req.user!.organizationId);
    res.json({ success: true, data });
  }
}

export const gdprController = new GdprController();
