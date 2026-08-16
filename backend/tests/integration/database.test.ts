import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { PrismaClient } from "@prisma/client";

// These are integration tests that require a running database
describe("Database Schema", () => {
  const prisma = new PrismaClient();

  beforeAll(async () => {
    await prisma.$connect();
  });

  afterAll(async () => {
    await prisma.$disconnect();
  });

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
