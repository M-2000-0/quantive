import { prisma } from "../../config/database";
import { logger } from "../../config/logger";

interface RegulatoryFramework {
  id: string;
  name: string;
  jurisdiction: string;
  requirements: RegRequirement[];
}

interface RegRequirement {
  id: string;
  name: string;
  description: string;
  satisfiedBy: string[]; // feature/module names
  evidenceType: "report" | "audit_log" | "case_finding" | "configuration";
}

const FRAMEWORKS: RegulatoryFramework[] = [
  {
    id: "fatf-travel-rule",
    name: "FATF Recommendation 16 — Travel Rule",
    jurisdiction: "Global",
    requirements: [
      { id: "fatf-1", name: "Originator identification", description: "Collect and hold originator's name, address, and account number", satisfiedBy: ["wallet_profiling", "transaction_logging"], evidenceType: "audit_log" },
      { id: "fatf-2", name: "Beneficiary identification", description: "Collect and hold beneficiary's name and account number", satisfiedBy: ["wallet_profiling", "transaction_logging"], evidenceType: "audit_log" },
      { id: "fatf-3", name: "Record keeping", description: "Maintain records for at least 5 years", satisfiedBy: ["immutable_audit_logs", "report_export"], evidenceType: "report" },
      { id: "fatf-4", name: "Suspicious transaction reporting", description: "Report suspicious transactions to FIU", satisfiedBy: ["alert_management", "case_management", "audit_trail_reporting"], evidenceType: "case_finding" },
    ],
  },
  {
    id: "mica",
    name: "EU MiCA — Markets in Crypto-Assets",
    jurisdiction: "European Union",
    requirements: [
      { id: "mica-1", name: "White paper publication", description: "Ensure crypto-asset white papers are published and notified", satisfiedBy: ["report_export"], evidenceType: "report" },
      { id: "mica-2", name: "Market abuse monitoring", description: "Detect and report market abuse patterns", satisfiedBy: ["real_time_monitoring", "risk_scoring", "alert_management"], evidenceType: "audit_log" },
      { id: "mica-3", name: "Conflict of interest management", description: "Identify and manage conflicts of interest", satisfiedBy: ["role_based_access", "audit_trail_reporting"], evidenceType: "configuration" },
      { id: "mica-4", name: "Transaction monitoring", description: "Monitor transactions for suspicious activity", satisfiedBy: ["real_time_monitoring", "transaction_logging", "risk_scoring"], evidenceType: "report" },
    ],
  },
  {
    id: "fincen-2013",
    name: "FinCEN — Crypto AML Requirements",
    jurisdiction: "United States",
    requirements: [
      { id: "fincen-1", name: "AML program", description: "Establish written AML program", satisfiedBy: ["case_management", "report_export"], evidenceType: "report" },
      { id: "fincen-2", name: "SAR filing", description: "File Suspicious Activity Reports for transactions over $5,000", satisfiedBy: ["alert_management", "case_management", "audit_trail_reporting"], evidenceType: "case_finding" },
      { id: "fincen-3", name: "Record keeping", description: "Maintain records of transmittals over $3,000", satisfiedBy: ["transaction_logging", "immutable_audit_logs"], evidenceType: "report" },
      { id: "fincen-4", name: "Travel Rule compliance", description: "Transmit originator/beneficiary info with transfers over $3,000", satisfiedBy: ["wallet_profiling", "transaction_logging"], evidenceType: "audit_log" },
    ],
  },
];

export class ComplianceFrameworkService {
  async getFrameworks() {
    return FRAMEWORKS.map((f) => ({
      id: f.id,
      name: f.name,
      jurisdiction: f.jurisdiction,
      requirementCount: f.requirements.length,
    }));
  }

  async getFrameworkDetail(frameworkId: string) {
    const framework = FRAMEWORKS.find((f) => f.id === frameworkId);
    if (!framework) return null;
    return framework;
  }

  async assessOrganization(organizationId: string) {
    const org = await prisma.organization.findUnique({
      where: { id: organizationId },
      include: {
        integrations: true,
        _count: { select: { transactions: true, alerts: true, cases: true } },
      },
    });
    if (!org) return null;

    const hasIntegrations = org.integrations.length > 0;
    const hasTransactions = org._count.transactions > 0;
    const hasAlerts = org._count.alerts > 0;
    const hasCases = org._count.cases > 0;

    const featureMap: Record<string, boolean> = {
      wallet_profiling: hasTransactions,
      transaction_logging: hasTransactions,
      immutable_audit_logs: true,
      report_export: false,
      alert_management: hasAlerts,
      case_management: hasCases,
      real_time_monitoring: hasIntegrations,
      risk_scoring: hasTransactions,
      role_based_access: true,
      audit_trail_reporting: false,
    };

    const results = FRAMEWORKS.map((fw) => {
      const satisfied = fw.requirements.filter((r) => r.satisfiedBy.some((f) => featureMap[f]));
      const compliance = Math.round((satisfied.length / fw.requirements.length) * 100);
      return {
        frameworkId: fw.id,
        frameworkName: fw.name,
        jurisdiction: fw.jurisdiction,
        compliance,
        satisfied: satisfied.length,
        total: fw.requirements.length,
        gaps: fw.requirements.filter((r) => !r.satisfiedBy.some((f) => featureMap[f])).map((r) => r.name),
      };
    });

    return results;
  }

  async generateComplianceReport(organizationId: string, frameworkId: string, traceId: string, userId?: string) {
    const assessment = await this.assessOrganization(organizationId);
    if (!assessment) throw Object.assign(new Error("Organization not found"), { statusCode: 404 });

    const fw = assessment.find((a) => a.frameworkId === frameworkId);
    if (!fw) throw Object.assign(new Error("Framework not found"), { statusCode: 404 });

    return fw;
  }
}

export const complianceFrameworkService = new ComplianceFrameworkService();
