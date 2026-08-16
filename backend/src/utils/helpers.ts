export function scoreToLevel(score: number): string {
  if (score > 0.75) return "CRITICAL";
  if (score > 0.5) return "HIGH";
  if (score >= 0.25) return "MEDIUM";
  return "LOW";
}

export function paginationHelper(page: number, limit: number) {
  const safePage = Math.max(1, page);
  const safeLimit = Math.min(Math.max(1, limit), 100);
  return {
    skip: (safePage - 1) * safeLimit,
    take: safeLimit,
    page: safePage,
    limit: safeLimit,
  };
}

export function asyncHandler(fn: (...args: unknown[]) => unknown) {
  return (req: any, res: any, next: any) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}

export function parsePagination(query: any) {
  const page = parseInt(query.page || "1", 10);
  const limit = parseInt(query.limit || "20", 10);
  const safePage = Math.max(1, page);
  const safeLimit = Math.min(Math.max(1, limit), 100);
  return {
    page: safePage,
    limit: safeLimit,
    skip: (safePage - 1) * safeLimit,
    sortBy: (query.sortBy as string) || "createdAt",
    sortOrder: (query.sortOrder as "asc" | "desc") || "desc",
  };
}
