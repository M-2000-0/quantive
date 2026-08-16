import { prisma } from "../../config/database";
import { auditService } from "../audit";

export class OnboardingService {
  async getStatus(organizationId: string) {
    const [integrationCount, walletCount, txCount, userCount, hasDemo] = await Promise.all([
      prisma.integration.count({ where: { organizationId } }),
      prisma.wallet.count({ where: { organizationId } }),
      prisma.transaction.count({ where: { organizationId } }),
      prisma.user.count({ where: { organizationId } }),
      prisma.transaction.count({ where: { organizationId, ingestedVia: "demo" } }),
    ]);

    const steps = [
      { id: "create_org", label: "Organization created", done: true },
      { id: "invite_team", label: "Invite team members", done: userCount >= 2 },
      { id: "connect_data", label: "Connect blockchain data", done: integrationCount > 0 },
      { id: "import_wallets", label: "Import monitored wallets", done: walletCount >= 3 },
      { id: "review_alerts", label: "Review first alerts", done: txCount > 0 },
      { id: "generate_report", label: "Generate first report", done: false },
    ];

    return {
      complete: steps.every((s) => s.done),
      progress: Math.round((steps.filter((s) => s.done).length / steps.length) * 100),
      steps,
      metrics: { integrations: integrationCount, wallets: walletCount, transactions: txCount, teamMembers: userCount, hasDemoData: hasDemo > 0 },
    };
  }

  async skipToDemo(organizationId: string, traceId: string, userId: string) {
    const { demoService } = await import("../demo");
    const result = await demoService.generateDemoData(organizationId);

    await auditService.log({
      organizationId,
      userId,
      action: "UPDATED",
      entityType: "organization",
      entityId: organizationId,
      description: "Onboarding skipped — demo data loaded",
      metadata: result,
      traceId,
    });

    return result;
  }
}

export const onboardingService = new OnboardingService();
