import { prisma } from "../config/database";
import { config } from "../config";
import { logger } from "../config/logger";
import { auditService } from "./audit";
import { stringify } from "csv-stringify/sync";
import PDFDocument from "pdfkit";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import { v4 as uuidv4 } from "uuid";
import { writeFileSync, existsSync, mkdirSync } from "fs";
import { join } from "path";

let s3: S3Client | null = null;
try {
  s3 = new S3Client({
    endpoint: config.s3.endpoint,
    region: config.s3.region,
    credentials: {
      accessKeyId: config.s3.accessKey,
      secretAccessKey: config.s3.secretKey,
    },
    forcePathStyle: true,
  });
} catch {
  logger.warn("S3 client init failed — reports will be saved locally");
}

const UPLOADS_DIR = join(__dirname, "../../uploads");
if (!existsSync(UPLOADS_DIR)) {
  mkdirSync(UPLOADS_DIR, { recursive: true });
}

export class ReportService {
  async generate(
    organizationId: string,
    type: string,
    format: string,
    parameters: any,
    traceId: string,
    userId?: string
  ) {
    const data = await this.fetchData(organizationId, type, parameters);

    let fileUrl: string;
    let fileSize: number;

    if (format === "csv") {
      const csvContent = this.toCsv(data, type);
      const result = await this.uploadFile(csvContent, `${type}_${uuidv4()}.csv`, "text/csv");
      fileUrl = result.url;
      fileSize = result.size;
    } else {
      const pdfBuffer = await this.toPdf(data, type);
      const result = await this.uploadFile(pdfBuffer, `${type}_${uuidv4()}.pdf`, "application/pdf");
      fileUrl = result.url;
      fileSize = result.size;
    }

    const report = await prisma.report.create({
      data: {
        title: `${type.replace(/_/g, " ")} report`,
        type,
        format,
        parameters: parameters ? JSON.stringify(parameters) : undefined,
        fileUrl,
        fileSize,
        organizationId,
        generatedById: userId || null,
      },
    });

    await auditService.log({
      organizationId,
      userId: userId || null,
      action: "REPORT_GENERATED",
      entityType: "report",
      entityId: report.id,
      description: `Report generated: ${type} (${format})`,
      metadata: { type, format, parameters },
      traceId,
    });

    return report;
  }

  async list(organizationId: string, query: any) {
    const p = Math.max(1, parseInt(query.page) || 1);
    const l = Math.min(Math.max(1, parseInt(query.limit) || 20), 100);
    const where: any = { organizationId };
    if (query.type) where.type = query.type;

    const [data, total] = await Promise.all([
      prisma.report.findMany({
        where,
        skip: (p - 1) * l,
        take: l,
        orderBy: { createdAt: "desc" },
        select: { id: true, title: true, type: true, format: true, fileUrl: true, fileSize: true, generatedAt: true, createdAt: true },
      }),
      prisma.report.count({ where }),
    ]);

    return { data, pagination: { page: p, limit: l, total, totalPages: Math.ceil(total / l) } };
  }

  private async fetchData(organizationId: string, type: string, parameters: any) {
    switch (type) {
      case "transaction_log": {
        const where: any = { organizationId };
        if (parameters?.startDate || parameters?.endDate) {
          where.timestamp = {};
          if (parameters.startDate) where.timestamp.gte = new Date(parameters.startDate);
          if (parameters.endDate) where.timestamp.lte = new Date(parameters.endDate);
        }
        return prisma.transaction.findMany({
          where,
          orderBy: { timestamp: "desc" },
          take: 10000,
          select: { txHash: true, chain: true, timestamp: true, fromAddress: true, toAddress: true, value: true, token: true, riskLevel: true, riskScore: true, riskReasonCodes: true },
        });
      }
      case "risk_overview": {
        const [wallets, transactions, alerts] = await Promise.all([
          prisma.wallet.findMany({ where: { organizationId }, select: { address: true, chain: true, riskLevel: true, riskScore: true, tags: true, firstSeenAt: true } }),
          prisma.transaction.groupBy({ by: ["riskLevel"], where: { organizationId }, _count: true }),
          prisma.alert.groupBy({ by: ["status", "severity"], where: { organizationId }, _count: true }),
        ]);
        return { wallets, transactionsByRisk: transactions, alertsByStatus: alerts };
      }
      case "case_summary": {
        const where: any = { organizationId };
        if (parameters?.status) where.status = parameters.status;
        return prisma.case.findMany({
          where,
          orderBy: { createdAt: "desc" },
          include: {
            assignee: { select: { name: true, email: true } },
            _count: { select: { alerts: true, comments: true } },
          },
        });
      }
      case "audit_trail": {
        const where: any = { organizationId };
        if (parameters?.action) where.action = parameters.action;
        return prisma.auditLog.findMany({
          where,
          orderBy: { createdAt: "desc" },
          take: 10000,
          include: { user: { select: { name: true, email: true } } },
        });
      }
      default:
        throw Object.assign(new Error(`Unknown report type: ${type}`), { statusCode: 400 });
    }
  }

  private toCsv(data: any, type: string): string {
    if (Array.isArray(data)) {
      if (data.length === 0) return "";
      return stringify(data, { header: true });
    }
    return stringify([data], { header: true });
  }

  private toPdf(data: any, type: string): Promise<Buffer> {
    return new Promise((resolve, reject) => {
      const doc = new PDFDocument({ margin: 50 });
      const chunks: Buffer[] = [];
      doc.on("data", (chunk) => chunks.push(chunk));
      doc.on("end", () => resolve(Buffer.concat(chunks)));
      doc.on("error", reject);

      doc.fontSize(18).text(`Quantive Report: ${type.replace(/_/g, " ")}`, { align: "center" });
      doc.moveDown();
      doc.fontSize(10).text(`Generated: ${new Date().toISOString()}`, { align: "right" });
      doc.moveDown(2);

      if (Array.isArray(data)) {
        const headers = Object.keys(data[0] || {});
        if (headers.length) {
          doc.fontSize(8).text(headers.join(" | "), { underline: true });
          doc.moveDown(0.5);
          data.slice(0, 500).forEach((row: any) => {
            const line = headers.map((h) => String(row[h] ?? "")).join(" | ");
            doc.fontSize(7).text(line);
          });
        }
      } else {
        doc.fontSize(10).text(JSON.stringify(data, null, 2));
      }

      doc.end();
    });
  }

  private async uploadFile(content: Buffer | string, filename: string, contentType: string) {
    const body = typeof content === "string" ? Buffer.from(content, "utf-8") : content;

    if (s3) {
      try {
        const key = `reports/${filename}`;
        await s3.send(
          new PutObjectCommand({
            Bucket: config.s3.bucket,
            Key: key,
            Body: body,
            ContentType: contentType,
          })
        );
        return {
          url: `${config.s3.endpoint}/${config.s3.bucket}/${key}`,
          size: body.length,
        };
      } catch (err) {
        logger.warn({ err }, "S3 upload failed, falling back to local storage");
      }
    }

    const localPath = join(UPLOADS_DIR, filename);
    writeFileSync(localPath, body);
    return {
      url: `/uploads/${filename}`,
      size: body.length,
    };
  }
}

export const reportService = new ReportService();