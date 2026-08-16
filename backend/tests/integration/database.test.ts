import { describe, it, expect, afterAll } from "vitest";
import { PrismaClient } from "@prisma/client";

// These are integration tests that require a running database (see CI: postgres service).
// Probe connectivity once at module load; without a reachable Postgres the whole suite
// is skipped instead of failing.
const prisma = new PrismaClient();

let dbAvailable = true;
try {
  await prisma.$connect();
} catch {
  dbAvailable = false;
}

afterAll(async () => {
  await prisma.$disconnect().catch(() => undefined);
});

describe.skipIf(!dbAvailable)("Database Schema", () => {
  it("can create an organization", async () => {
    const org = await prisma.organization.create({
      data: { name: "Test Org", slug: `test-${Date.now()}` },
    });
    expect(org.id).toBeDefined();
    expect(org.name).toBe("Test Org");
    await prisma.organization.delete({ where: { id: org.id } });
  });

  it("enforces unique slugs", async () => {
    const slug = `dup-${Date.now()}`;
    await prisma.organization.create({ data: { name: "A", slug } });
    await expect(
      prisma.organization.create({ data: { name: "B", slug } })
    ).rejects.toThrow();
    await prisma.organization.deleteMany({ where: { slug } });
  });
});
