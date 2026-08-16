import { prisma } from "../config/database";
import { logger } from "../config/logger";

/**
 * GDPR/DSAR erasure for a whole organization.
 *
 * Deletes every piece of organization-scoped data in dependency order:
 * comments → cases → alerts → reports → transactions → wallets →
 * webhook deliveries → webhook endpoints → integrations → audit logs →
 * users → roles → subscriptions → organization.
 *
 * Nothing is soft-deleted; this is a hard, auditable right-to-erasure.
 */
export async function deleteOrganizationData(organizationId: string) {
  const counts: Record<string, number> = {};

  counts.comments = (await prisma.comment.deleteMany({ where: { case: { organizationId } } })).count;
  counts.cases = (await prisma.case.deleteMany({ where: { organizationId } })).count;
  counts.alerts = (await prisma.alert.deleteMany({ where: { organizationId } })).count;
  counts.reports = (await prisma.report.deleteMany({ where: { organizationId } })).count;
  counts.transactions = (await prisma.transaction.deleteMany({ where: { organizationId } })).count;
  counts.wallets = (await prisma.wallet.deleteMany({ where: { organizationId } })).count;

  const endpoints = await prisma.webhookEndpoint.findMany({ where: { organizationId }, select: { id: true } });
  counts.webhookDeliveries = (
    await prisma.webhookDelivery.deleteMany({ where: { endpointId: { in: endpoints.map((e) => e.id) } } })
  ).count;
  counts.webhookEndpoints = (await prisma.webhookEndpoint.deleteMany({ where: { organizationId } })).count;
  counts.integrations = (await prisma.integration.deleteMany({ where: { organizationId } })).count;

  // Audit logs are erased too; a single erasure receipt is returned to the caller instead.
  counts.auditLogs = (await prisma.auditLog.deleteMany({ where: { organizationId } })).count;
  counts.users = (await prisma.user.deleteMany({ where: { organizationId } })).count;
  counts.roles = (await prisma.role.deleteMany({ where: { organizationId } })).count;
  counts.subscriptions = (await prisma.subscription.deleteMany({ where: { organizationId } })).count;
  counts.organization = (await prisma.organization.deleteMany({ where: { id: organizationId } })).count;

  logger.info({ organizationId, counts }, "GDPR erasure complete");
  return { organizationId, deleted: counts, erasedAt: new Date().toISOString() };
}

/**
 * Data export (right of access): dump all org-scoped rows as plain objects
 * for a DSAR response package.
 */
export async function exportOrganizationData(organizationId: string) {
  const [organization, wallets, transactions, alerts, cases, reports, integrations, users, auditLogs] =
    await Promise.all([
      prisma.organization.findUnique({ where: { id: organizationId } }),
      prisma.wallet.findMany({ where: { organizationId } }),
      prisma.transaction.findMany({ where: { organizationId } }),
      prisma.alert.findMany({ where: { organizationId } }),
      prisma.case.findMany({ where: { organizationId } }),
      prisma.report.findMany({ where: { organizationId } }),
      prisma.integration.findMany({ where: { organizationId } }),
      prisma.user.findMany({ where: { organizationId } }),
      prisma.auditLog.findMany({ where: { organizationId } }),
    ]);

  return {
    organization,
    wallets,
    transactions,
    alerts,
    cases,
    reports,
    integrations,
    users: users.map(({ passwordHash, refreshToken, ...safe }) => safe),
    auditLogs,
    exportedAt: new Date().toISOString(),
  };
}
