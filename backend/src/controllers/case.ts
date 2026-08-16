import { Response } from "express";
import { AuthenticatedRequest } from "../types";
import { caseService } from "../services/case";
import { parsePagination } from "../utils/helpers";

export class CaseController {
  async create(req: AuthenticatedRequest, res: Response) {
    const case_ = await caseService.create(
      req.user!.organizationId,
      req.body,
      req.traceId!,
      req.user!.userId
    );
    res.status(201).json({ success: true, data: case_ });
  }

  async list(req: AuthenticatedRequest, res: Response) {
    const result = await caseService.list(req.user!.organizationId, req.query);
    res.json({ success: true, ...result });
  }

  async getById(req: AuthenticatedRequest, res: Response) {
    const case_ = await caseService.getById(req.user!.organizationId, String(req.params.id));
    res.json({ success: true, data: case_ });
  }

  async update(req: AuthenticatedRequest, res: Response) {
    const case_ = await caseService.update(
      req.user!.organizationId,
      String(req.params.id),
      req.body,
      req.traceId!,
      req.user!.userId
    );
    res.json({ success: true, data: case_ });
  }

  async addComment(req: AuthenticatedRequest, res: Response) {
    const comment = await caseService.addComment(
      req.user!.organizationId,
      String(req.params.id),
      req.body.content,
      req.traceId!,
      req.user!.userId
    );
    res.status(201).json({ success: true, data: comment });
  }
}

export const caseController = new CaseController();
