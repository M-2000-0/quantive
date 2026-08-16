import { PrismaClient } from "@prisma/client";
import bcrypt from "bcryptjs";

const prisma = new PrismaClient();

async function main() {
  const org = await prisma.organization.upsert({
    where: { slug: "quantive-demo" },
    update: {},
    create: { name: "Quantive Demo", slug: "quantive-demo" },
  });

  const adminRole = await prisma.role.upsert({
    where: { organizationId_name: { organizationId: org.id, name: "Admin" } },
    update: {},
    create: {
      name: "Admin",
      organizationId: org.id,
      isSystem: true,
      permissions: JSON.stringify([
        "users:read", "users:write", "users:delete",
        "transactions:read", "transactions:write",
        "wallets:read", "wallets:write",
        "alerts:read", "alerts:write", "alerts:dismiss",
        "cases:read", "cases:write", "cases:assign", "cases:close",
        "reports:read", "reports:write", "reports:export",
        "integrations:read", "integrations:write",
        "audit:read",
        "settings:read", "settings:write",
      ]),
    },
  });

  const analystRole = await prisma.role.upsert({
    where: { organizationId_name: { organizationId: org.id, name: "Analyst" } },
    update: {},
    create: {
      name: "Analyst",
      organizationId: org.id,
      isSystem: true,
      permissions: JSON.stringify([
        "transactions:read",
        "wallets:read",
        "alerts:read", "alerts:write", "alerts:dismiss",
        "cases:read", "cases:write", "cases:assign",
        "reports:read",
        "audit:read",
      ]),
    },
  });

  const viewerRole = await prisma.role.upsert({
    where: { organizationId_name: { organizationId: org.id, name: "Viewer" } },
    update: {},
    create: {
      name: "Viewer",
      organizationId: org.id,
      isSystem: true,
      permissions: JSON.stringify([
        "transactions:read",
        "wallets:read",
        "alerts:read",
        "cases:read",
        "reports:read",
        "audit:read",
      ]),
    },
  });

  const passwordHash = await bcrypt.hash("password123", 12);

  await prisma.user.upsert({
    where: { email: "admin@quantive.io" },
    update: {},
    create: {
      email: "admin@quantive.io",
      passwordHash,
      name: "Admin User",
      organizationId: org.id,
      roleId: adminRole.id,
    },
  });

  await prisma.user.upsert({
    where: { email: "analyst@quantive.io" },
    update: {},
    create: {
      email: "analyst@quantive.io",
      passwordHash,
      name: "Analyst User",
      organizationId: org.id,
      roleId: analystRole.id,
    },
  });

  console.log("Seed completed successfully");
  console.log("  Org: quantive-demo");
  console.log("  Admin: admin@quantive.io / password123");
  console.log("  Analyst: analyst@quantive.io / password123");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
